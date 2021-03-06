from flask.helpers import make_response
from sqlalchemy.orm import eagerload
from app.forms import ProctorSessionForm, ExamFormForm
from app import db
from app.models import ProctorSession, SessionUser, ExamForm, Log, User
from flask import Blueprint, render_template, redirect, url_for, json
from flask_login import login_required, current_user
from datetime import datetime
from pytz import timezone

from app.blueprint.helper.email_helpers import mail_all

bp = Blueprint("proctor", __name__, url_prefix="/proctor")

IST = timezone("asia/kolkata")
UTC = timezone('utc')

def localToUtc(date):
    return IST.localize(date).astimezone(UTC)

@bp.route("/", methods=["GET"])
@login_required
def index():
    ps = current_user.proctor_sessions
    now = UTC.localize(datetime.utcnow())
    return render_template("proctor_home.html",proctor_session_data=ps, now=now, user_type=current_user.user_type)



@bp.route("/session/create", methods=["GET", "POST"])
@login_required 
def session_create():
    form = ProctorSessionForm()
    if form.validate_on_submit():
        session_name = form.session_name.data
        start_time = localToUtc(form.start_time.data)
        end_time = localToUtc(form.end_time.data)
        duration = (end_time - start_time).total_seconds()
        token_duration = (end_time - localToUtc(datetime.now())).total_seconds()
        print(start_time,end_time,duration)
        #create a Proctor Session
        print(start_time, end_time)
        ps = ProctorSession(name=session_name, start_time=start_time, end_time=end_time, duration=duration, user_id=current_user)
        db.session.add(ps)
        susers = []
        for suser in form.session_users:
             details = {}
             details['disable_eye_detection'] = suser.disable_eye_detection.data

             user = SessionUser(
                                name=suser.username.data, 
                                email=suser.email.data, 
                                proctor_session=ps, 
                                token="token not set yet",
                                details=json.dumps(details)
                            )
             db.session.add(user)
             susers.append(user)
        db.session.commit() #commit changes to db so that ids are assigned.

        for suser in susers:
            suser.generate_auth_token(token_duration)
            db.session.add(suser)
        db.session.commit()

        return redirect(url_for("proctor.index"))
    else:
        return render_template("proctor_session_creator.html", form=form)

@bp.route("/session/details/<id>")
@login_required
def session_details(id):
    proctor_session = ProctorSession.query.get(id)
    if proctor_session is None:
        return "Session not Found"
    else:
        form_description = None
        if proctor_session.exam_form.count() > 0 :
            exam_form = list(proctor_session.exam_form)[0]
            form_description = exam_form.form_description
        session_users = list(proctor_session.session_users)
        for su in session_users:
            if su.submitted:
                log = Log.query.filter_by(token=su.token).first()
                headers = ["log_id"]+ list(log.proctoring_logs[0].keys())
                headers.remove("frame_id")
                face_not_detected = 0
                face_not_recognized = 0
                face_multi = 0 
                frame=1
                face_sideways = 0
                eye_sideways = 0
                for x in log.proctoring_logs:
                    if "face_detection" not in x:
                        continue
                    frame+=1
                    if(x['face_detection'] == "False"):
                        face_not_detected += 1
                    if(x['face_recognition'] == "False"):
                        face_not_recognized += 1           
                    if(x['multiple_face'] == "True"):
                        face_multi += 1
                    if(x["face_alignment"] == "left" or x['face_alignment'] == "right"):
                        face_sideways += 1
                    if(x['eye_position'] == "left" or x['eye_position'] == "right"):
                        eye_sideways += 1

                face_not_detected/=frame*(1/100)
                face_multi/=frame*(1/100)
                face_not_recognized/=frame*(1/100)
                face_sideways/=frame*(1/100)
                eye_sideways/=frame*(1/100)
                round_2 = lambda x: round(x, 2)
                log_data = [log.id, face_not_detected, face_multi, face_not_recognized, face_sideways, eye_sideways]
                log_data = list(map(round_2, log_data ))
                log_data = list(map(str, log_data))
                print(log_data)
                su.log_data = log_data
        return render_template("proctor_session_details.html", data = proctor_session, session_users=session_users, exam_form = form_description)


@bp.route("/session/<int:proctor_id>/mail/<string:user_id>")
@bp.route("/session/<int:proctor_id>/mail/")
def mail_session_user(proctor_id, user_id=None):
    proctor_session = ProctorSession.query.get(proctor_id)
    if proctor_session is None:
        return make_response({"msg":"proctor sesssion not found"}, 404)
    
    target_user_list = []

    if user_id is None:
        target_user_list=proctor_session.session_users
    else:
        target_user = SessionUser.query.with_parent(proctor_session).filter_by(id=user_id).first()
        if target_user is None:
            return make_response({'msg':"user id not found"}, 404)
        target_user_list = [target_user]
    mail_all(proctor_session, target_user_list)
    return make_response({"msg":"Success"}, 200)

@bp.route("/exam_form/create/",methods=['GET',"POST"])
@login_required
def exam_form_create():
    form = ExamFormForm()
    form.proctor_id.choices = [(x.id, x.name) for x in current_user.proctor_sessions]
    if form.validate_on_submit():
        questions = []
        proctor_id = form.proctor_id.data
        
        target_proctor_session = ProctorSession.query.get(proctor_id)
        id = 0
        for exam_question in form.exam_questions:
            q = {"id":id, "question_text": exam_question.question.data}
            questions.append(q)
            id+=1
        form_description = { 'exam_questions':questions }
        exam_form = ExamForm(user_id=current_user, proctor_session=target_proctor_session, form_description=form_description)
        
        db.session.add(exam_form)
        db.session.commit()

        return redirect(url_for("proctor.index"))
    return render_template("exam_form_create.html", form=form)

@bp.route("/session/purge/<int:proctor_id>")
@login_required
def purge_session(proctor_id):
    proctor_session = ProctorSession.query.get(proctor_id)
    for session_user in proctor_session.session_users.all():
        if session_user.exam_response is not None:
            db.session.delete(session_user.exam_response)
        db.session.delete(session_user)
    for exam_form in proctor_session.exam_form.all():
        db.session.delete(exam_form)
    db.session.delete(proctor_session)
    db.session.commit()
    return redirect(url_for("proctor.index"))
        
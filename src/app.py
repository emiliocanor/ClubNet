import secrets
from flask import Flask, render_template, redirect, request, url_for, jsonify, flash, session
from sys import path
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
import admin
import posts
import profile
import sqlalchemy
from flask_mail import Mail, Message
from CASClient import CASClient

CLUB_SOCC = 1
INVALID = 0
REQUEST = 1
VALIDATED = 2
ADMIN = 3

# app info
app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(16)
os.environ['DB_URL']="postgres://oxifvfuc:3Z_OtccJkuJzjE4je2oRnEe3LE47Ksgk@peanut.db.elephantsql.com/oxifvfuc"
os.environ['CLOUDINARY_URL']="cloudinary://375874577914178:bAM3VvtO-xWQCB_TIdgZ--bhG5Y@clubnet"
os.environ['API_KEY']="375874577914178"
os.environ['API_SECRET']="bAM3VvtO-xWQCB_TIdgZ--bhG5Y"
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'ClubNetPrinceton@gmail.com'
app.config['MAIL_PASSWORD'] = 'rzylxkhufcffwzxo'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

#databasen connection
DATABASE_URL = os.getenv('DB_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
engine = sqlalchemy.create_engine(DATABASE_URL)


@app.route('/')
def hello():
    return render_template('landing.html')


@app.route('/home')
def home():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))
    net_id = response[0]
    print(session.get('username'))
    user = profile.get_profile_from_id(engine, net_id)
    img = user.profile_image_url
    member_count, alumni_count = profile.get_club_member_count(engine, CLUB_SOCC)
    return render_template('home.html', CASValue=response[0], validation=response[1], img=img, member_count=member_count, alumni_count=alumni_count)


@app.route("/pending_request")
def pending_request():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == VALIDATED:
        return redirect(url_for('home'))
    if response[1] == ADMIN:
        return redirect(url_for('home'))

    admins = admin.get_admins(engine)
    print(admins)
    return render_template('pending_request.html', CASValue=response[0],validation=response[1], admins = admins)


@app.route("/invalid", methods=['GET'])
def invalid():
    response = validate_user(CLUB_SOCC)
    if response[1] == VALIDATED:
        return redirect(url_for('home'))
    if response[1] == ADMIN:
        return redirect(url_for('home'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))
    return render_template('invalid.html', CAS_Value=response[0],validation=response[1])

@app.route("/process_request", methods=['GET', 'POST'])
def process_request():
    netid = request.args.get('user_id', None)
    name = request.form.get('name', None)
    year = request.form.get('year', None)
    email = request.form.get('email', None)
    print("process request", name, year, email)
    # this probably needs to be worked on further, not sure how this
    # affects alumni accounts
    if name == '' or year == '' or year.isnumeric() == False or email == '':
        flash('please enter valid, nonempty personal information')
        return redirect(url_for('invalid'))
    else:
        profile.create_profile(engine, netid, name, year, email)
        admin.create_request(engine, netid, CLUB_SOCC, name, year, email)

         # sends email to user after requests to join
        messagetwo = Message("Your User Request on ClubNet!",sender ='ClubNetPrinceton@gmail.com', recipients = [email])
        messagetwo.body = 'You are being notified because your request to join Club Soccer on ClubNet is now pending! You will be notified again if you are approved! \n \n '
        messagetwo.body += "Best regards,\n"
        messagetwo.body += "The ClubNet Team\n"
        messagetwo.body += "clubnet.onrender.com"
        mail.send(messagetwo)
        print("SENT AN EMAIL")

        # sends email to admins for new pending join requests
        admins = admin.get_admins(engine)
        print(admins)
        print("I know there's this admin here")
        recipientlistone = []
        for each_admin in admins:
            if each_admin.get_email() != "None":
                email = each_admin.get_email()
                recipientlistone.append(email)
        print(recipientlistone)
        message = Message("New User Request on ClubNet!",sender ='ClubNetPrinceton@gmail.com', recipients = recipientlistone)
        message.body = 'You are being notified because a new user has made a request to join Club Soccer on ClubNet that needs to be processed! \n \n To view the contents of this new request, go to https://clubnet.onrender.com/admin.\n \n '
        message.body += "Best regards,\n"
        message.body += "The ClubNet Team\n"
        message.body += "clubnet.onrender.com"
        mail.send(message)
        print("SENT AN EMAIL")

        return redirect(url_for('pending_request'))


@app.route('/members', methods=['GET', 'POST'])
def members():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))
    net_id = response[0]
    user = profile.get_profile_from_id(engine, net_id)
    img = user.profile_image_url
    return render_template('members.html', img=img, validation=response[1])

@app.route('/memberlist')
def member_list():
    name = request.args.get("name", None)
    year = request.args.get("year", None)
    major = request.args.get("major", None)
    industry = request.args.get("industry", None)
    status_filter = int(request.args.get("filter", None))
    print(type(year))
    # print(name)
    members = profile.get_profiles_from_club_filtered(engine, CLUB_SOCC, name, year, status_filter,major, industry)
    # print("I am returning the member template")
    # print(members)
    return render_template("member_list.html", members=members)

@app.route('/get_announcements')
def get_announcements():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))
    filter = request.args.get("filter", None)
    netid = request.args.get("id", None)
    page_number = request.args.get("page_number", None)
    print("page pls", page_number)
    if page_number:
        page_number = int(page_number)
    else:
        page_number = 1
    post_values, num_pages = posts.get_posts(engine, response[0], filter, page_number, True)
    isAdmin = admin.is_admin(engine, netid, CLUB_SOCC)
    return render_template('announcement_list.html', posts=post_values, isAdmin=isAdmin, page_number=page_number, num_pages=num_pages)

@app.route('/announcements', methods=['GET', 'POST'])
def announcements():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))

    page_number = request.args.get("page_number", None)
    print("page pls", page_number)
    if page_number:
        page_number = int(page_number)
    else:
        page_number = 1
    filter = request.args.get("filter", None)
    post_values, num_pages = posts.get_posts(engine, response[0], filter, page_number, True)
    net_id = response[0]
    user = profile.get_profile_from_id(engine, net_id)
    img = user.profile_image_url
    members = profile.get_profiles_from_club(engine, CLUB_SOCC)
    isAdmin = admin.is_admin(engine, net_id, CLUB_SOCC)
    return render_template('announcements.html', posts=post_values, img=img, validation=response[1], isAdmin=isAdmin, user=user, filter=filter, netid = net_id, page_number=page_number, num_pages=num_pages)

@app.route('/announcements/delete', methods=['GET', 'POST', 'DELETE'])
def delete_post():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))

    post_id = request.args.get("post_id", None)
    posts.delete_post(engine, post_id)
    return redirect(url_for('announcements'))

@app.route('/announcements/like', methods=['GET'])
def like():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))

    post_id = request.args.get("post_id", None)
    posts.like(engine, post_id, response[0])
    return redirect(url_for('announcements'))

@app.route('/announcements/unlike', methods=['GET'])
def unlike():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))

    post_id = request.args.get("post_id", None)
    posts.unlike(engine, post_id, response[0])
    return redirect(url_for('announcements'))

@app.route('/announcements/comment', methods=['GET'])
def comment():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))

    comment = request.args.get("comment-input", None)
    post_id = request.args.get("post_id", None)
    posts.comment(engine, post_id, response[0], comment)
    return redirect(url_for('announcements'))


@app.route('/profile')
def profiles():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))
    net_id = request.args.get("net_id", None)
    user = profile.get_profile_from_id(engine, net_id)
    cover_net_id = response[0]
    cover_user = profile.get_profile_from_id(engine, cover_net_id)
    img = cover_user.profile_image_url
    members = profile.get_profiles_from_club(engine, CLUB_SOCC)
    return render_template('profile.html', user=user, img=img, validation=response[1])

@app.route('/myprofile', methods=["GET", "POST"])
def myProfile():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))
    net_id = CASClient().Authenticate()
    user = profile.get_profile_from_id(engine, net_id)
    img = user.profile_image_url
    members = profile.get_profiles_from_club(engine, CLUB_SOCC)
    if request.method == 'POST':
        print(request.form.get('notifications'))
        print(request.form)
        profile.edit_profile(engine, net_id, request.form)
        return redirect(url_for('members'))
    return render_template('myprofile.html', user=user, img=img, validation=response[1])


@app.route('/donations')
def donations():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))
    net_id = response[0]
    user = profile.get_profile_from_id(engine, net_id)
    img = user.profile_image_url
    members = profile.get_profiles_from_club(engine, CLUB_SOCC)
    return render_template('donations.html', img=img, validation=response[1])


@app.route('/admin', methods=['GET', 'POST'])
def admin_page():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))
    if response[1] == VALIDATED:
        return redirect(url_for("home"))
    pendingRequests = admin.get_requests(engine)
    postRequests = posts.get_post_requests(engine)
    net_id = response[0]
    user = profile.get_profile_from_id(engine, net_id)
    img = user.profile_image_url
    members = profile.get_profiles_from_club(engine, CLUB_SOCC)
    all_members = 'mailto:'
    students = 'mailto:'
    alumni = 'mailto:'
    for member in members:
        if member.get_email() != "None":
                all_members += member.get_email() + ','
                if member.is_alumni():
                    alumni += member.get_email() + ','
                else:
                    students += member.get_email() + ','

    return render_template('admin.html', members=members, requests=pendingRequests, posts = postRequests, validation=response[1], img=img, all_members = all_members, students = students, alumni = alumni)


@app.route('/admin/accept', methods=['GET'])
# response.set_cookie('previous_search', ("/?dept=" + str(dept) +
# "&coursenum=" + str(coursenum) + "&area=" + str(area) +
# "&title=" + str(title)))
#  previous_search = flask.request.cookies.get('previous_search')
def admin_accept_page():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))
    if response[1] == VALIDATED:
        return redirect(url_for("home"))

    user_id = request.args.get("user_id", None)
    email = admin.get_request_email(engine, user_id)
    print("process request", email)
    admin.approve_request(engine, user_id, CLUB_SOCC)
    print("sucessfully approved")

    # sends email to user if they have newly been validated
    message = Message("Request Approved on ClubNet!",sender ='ClubNetPrinceton@gmail.com', recipients = [email])
    print("message created")
    message.body = 'You are being notified because your request to join Club Soccer on ClubNet has been approved! \n \n To log in, go to https://clubnet.onrender.com.\n \n '
    message.body += "Best regards,\n"
    message.body += "The ClubNet Team\n"
    message.body += "clubnet.onrender.com"
    mail.send(message)
    print("SENT AN EMAIL")
    return redirect(url_for('admin_page'))

@app.route('/admin/deny', methods=['GET'])
def admin_deny_page():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))
    if response[1] == VALIDATED:
        return redirect(url_for("home"))

    user_id = request.args.get("user_id", None)
    admin.delete_request(engine, user_id, CLUB_SOCC)
    return redirect(url_for('admin_page'))

@app.route('/form', methods=['GET', 'POST'])
def render_form():
    if request.method == 'POST':
        # make the post
        # then send them to add image
        print(request)
        response = validate_user(CLUB_SOCC)
        id = posts.make_request(engine, request.form.get('Post Title'),request.form.get('Post Description'), response[0])
        return redirect(url_for('base_upload',post_id=id))
    return render_template("form.html")

@app.route('/admin/remove_user', methods=["POST"])
def remove_user():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))
    if response[1] == VALIDATED:
        return redirect(url_for("home"))
    net_id = request.form.get("user_id", None)
    admin.remove_user(engine, net_id, CLUB_SOCC)
    return redirect(url_for('admin_page'))

@app.route('/admin/remove_admin', methods=["POST"])
def remove_admin():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))
    if response[1] == VALIDATED:
        return redirect(url_for("home"))
    net_id = request.form.get("user_id", None)
    admin.remove_admin(engine, net_id, CLUB_SOCC)
    return redirect(url_for('admin_page'))

@app.route('/admin/make_admin', methods=["POST"])
def make_admin():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))
    if response[1] == VALIDATED:
        return redirect(url_for("home"))
    net_id = request.form.get("user_id", None)
    officer_position = request.form.get("off_pos", None)
    admin.make_admin(engine, net_id, CLUB_SOCC, officer_position)
    return redirect(url_for('admin_page'))

@app.route('/admin/accept_post', methods=["GET"])
def accept_post():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))
    if response[1] == VALIDATED:
        return redirect(url_for("home"))
    post_id = request.args.get("post_id", None)


    posts.approve_post_request(engine, post_id)

    # does get_post_by_id work?
    # alternatively, could retrieve all posts and just use last post in list as new_post
    post_values = posts.get_posts(engine, response[0], None)
    new_post = post_values[0]['post']
    print(new_post)
    # new_post = posts.get_post_by_id(engine, post_id)

    # inserting logic here to send out the info for a post
    recipientlist = []
    print("I know there's this user here")
    for person in profile.get_profiles_from_club(engine, CLUB_SOCC):
        if person.get_email() != "None":
            if(person.get_notifications() == "true"):
                email = person.get_email()
                recipientlist.append(email)
    print(recipientlist)


    print("SENT AN EMAIL")
    message = Message("New Post on ClubNet!",sender ='ClubNetPrinceton@gmail.com', recipients = recipientlist)
    message.body = 'You are being notified because a new post has been made for Club Soccer on ClubNet! \n \n To view the contents of the new post, go to https://clubnet.onrender.com/announcements.\n \n '
    message.body += "Best regards,\n"
    message.body += "The ClubNet Team"
    message.body += "clubnet.onrender.com"
    # message.html = render_template("message.html", post=new_post)
    mail.send(message)

    return redirect(url_for('admin_page'))

@app.route('/admin/deny_post', methods=["GET"])
def deny_post():
    response = validate_user(CLUB_SOCC)
    if response[1] == INVALID:
        return redirect(url_for('invalid'))
    if response[1] == REQUEST:
        return redirect(url_for('pending_request'))
    if response[1] == VALIDATED:
        return redirect(url_for("home"))
    post_id = request.args.get("post_id", None)
    posts.reject_request(engine, post_id)
    return redirect(url_for('admin_page'))


def validate_user(club_id):
    netid = CASClient().Authenticate()
    is_in_club = profile.validate(engine, netid, club_id)
    if is_in_club:
        if admin.is_admin(engine, netid, club_id):
            return (netid, ADMIN)
        else:
            return (netid, VALIDATED)
    else:
        is_in_requests = admin.check_request(engine, netid, CLUB_SOCC)
        if is_in_requests:
            return (netid, REQUEST)
        else:
            return (netid, INVALID)

# WIP here about the uploading of images
@app.route("/upload_post_image", methods=['POST', 'GET'])
def upload_file():
    # netid = CASClient().Authenticate()
    file_cloudinary_link = ""
    post_id = request.args.get('post_id')
    app.logger.info('in upload route')

    cloudinary.config(cloud_name = 'clubnet', api_key=os.getenv('API_KEY'),
    api_secret=os.getenv('API_SECRET'))
    upload_result = None
    if request.method == 'POST':
        file_to_upload = request.files['file']
        app.logger.info('%s file_to_upload', file_to_upload)

    if file_to_upload:
        upload_result = cloudinary.uploader.upload(file_to_upload)
        app.logger.info(upload_result)
        print(jsonify(upload_result))
        file_cloudinary_link = upload_result['url']
        # print(file_cloudinary_link)
        if file_cloudinary_link != None:
            posts.add_image(engine, post_id, file_cloudinary_link)
            response = validate_user(CLUB_SOCC)
            post_values = posts.get_posts(engine, response[0], None)
            print("I AM HERE, I have a cloudinary link")
            return redirect(url_for('home'))
    return jsonify(upload_result)

@app.route("/upload_post_image_page")
def base_upload():
    response = validate_user(CLUB_SOCC)
    post_id = request.args.get('post_id')
    cover_user = profile.get_profile_from_id(engine, response[0])
    img = cover_user.profile_image_url

    # sends email to admins for new posts suggested
    admins = admin.get_admins(engine)
    print(admins)
    print("I know there's this admin here")
    recipientlist = []
    for each_admin in admins:
        if each_admin.get_email() != "None":
            email = each_admin.get_email()
            recipientlist.append(email)
    print(recipientlist)
    print("SENT AN EMAIL")
    message = Message("New Post Suggested on ClubNet!",sender ='ClubNetPrinceton@gmail.com', recipients = recipientlist)
    message.body = 'You are being notified because a user has suggested a new post in Club Soccer on ClubNet! \n \n To approve or decline, go to https://clubnet.onrender.com/admin.\n \n '
    message.body += "Best regards,\n"
    message.body += "The ClubNet Team\n"
    message.body += "clubnet.onrender.com"
    # message.html = render_template("message.html", post=new_post)
    mail.send(message)

    return render_template("image_upload.html", post_id=post_id, validation=response[1], img=img)

@app.route("/upload_profile_image_page")
def profile_image_url():
    response = validate_user(CLUB_SOCC)
    cover_user = profile.get_profile_from_id(engine, response[0])
    img = cover_user.profile_image_url
    return render_template("profile_image_upload.html", validation=response[1], img=img)

@app.route("/upload_profile_image", methods=['POST', 'GET'])
def upload_profile_image():
    # netid = CASClient().Authenticate()
    file_cloudinary_link = ""
    user_id = request.args.get('user_id')

    cloudinary.config(cloud_name = 'clubnet', api_key=os.getenv('API_KEY'),
    api_secret=os.getenv('API_SECRET'))
    upload_result = None
    if request.method == 'POST':
        file_to_upload = request.files['file']
        # app.logger.info('%s file_to_upload', file_to_upload)

    if file_to_upload:
        upload_result = cloudinary.uploader.upload(file_to_upload)
        app.logger.info(upload_result)
        print(jsonify(upload_result))
        file_cloudinary_link = upload_result['url']
        # print(file_cloudinary_link)
        if file_cloudinary_link != None:
            response = validate_user(CLUB_SOCC)
            profile.edit_profile_image(engine, response[0], file_cloudinary_link)
            # post_values = posts.get_posts(engine, response[0], None)
            print("updated with a cloudinary link")
            return redirect(url_for('home'))
    return jsonify(upload_result)

# -----------------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='localhost', port=5555, debug=True)
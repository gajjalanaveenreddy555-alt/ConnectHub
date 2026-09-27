from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

from werkzeug.utils import secure_filename

app = Flask(__name__)

@app.context_processor
def notification_count():

    if "user_id" not in session:
        return {
            "unread_notifications": 0
        }

    connection = get_db_connection()

    unread_notifications = connection.execute(
        """
        SELECT COUNT(*)
        FROM notifications
        WHERE user_id = ?
        AND is_read = 0
        """,
        (session["user_id"],)
    ).fetchone()[0]

    connection.close()

    return {
        "unread_notifications": unread_notifications
    }


# Secret key for login sessions
app.secret_key = "connecthub_secret_key"

DATABASE = "database.db"


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db_connection():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    connection = get_db_connection()

    posts = connection.execute(
        """
        SELECT
            posts.*,
            users.name,
            users.username,

            (
                SELECT COUNT(*)
                FROM likes
                WHERE likes.post_id = posts.id
            ) AS like_count,

            (
                SELECT COUNT(*)
                FROM comments
                WHERE comments.post_id = posts.id
            ) AS comment_count

        FROM posts

        JOIN users
        ON posts.user_id = users.id

        ORDER BY posts.id DESC
        """
    ).fetchall()


    # Get comments for every post
    post_list = []

    for post in posts:

        comments = connection.execute(
            """
            SELECT
                comments.*,
                users.name,
                users.username

            FROM comments

            JOIN users
            ON comments.user_id = users.id

            WHERE comments.post_id = ?

            ORDER BY comments.id ASC
            """,
            (post["id"],)
        ).fetchall()


        post_data = dict(post)

        post_data["comments"] = comments

        post_list.append(post_data)


    connection.close()


    return render_template(
        "index.html",
        posts=post_list,
    )

# ==========================================
# REGISTER
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        connection = get_db_connection()

        existing_user = connection.execute(
            """
            SELECT * FROM users
            WHERE username = ? OR email = ?
            """,
            (username, email)
        ).fetchone()

        if existing_user:

            connection.close()

            return render_template(
                "register.html",
                error="Username or email already exists."
            )

        connection.execute(
            """
            INSERT INTO users
            (name, username, email, password)
            VALUES (?, ?, ?, ?)
            """,
            (name, username, email, password)
        )

        connection.commit()
        connection.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        connection = get_db_connection()

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE username = ? AND password = ?
            """,
            (username, password)
        ).fetchone()

        connection.close()

        if user:

            session.clear()

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["name"] = user["name"]

            return redirect(url_for("home"))

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    return render_template("login.html")


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ==========================================
# PROFILE
# ==========================================

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    # Get current user
    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (session["user_id"],)
    ).fetchone()

    # Count user's posts
    post_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM posts
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()[0]

    # Count followers
    follower_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM followers
        WHERE following_id = ?
        """,
        (session["user_id"],)
    ).fetchone()[0]

    # Count following
    following_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM followers
        WHERE follower_id = ?
        """,
        (session["user_id"],)
    ).fetchone()[0]

    # Get user's posts
    posts = connection.execute(
        """
        SELECT
            posts.*,
            users.name,
            users.username
        FROM posts
        JOIN users
        ON posts.user_id = users.id
        WHERE posts.user_id = ?
        ORDER BY posts.id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    connection.close()

    return render_template(
        "profile.html",
        user=user,
        post_count=post_count,
        follower_count=follower_count,
        following_count=following_count,
        posts=posts
    )


@app.route("/edit-profile", methods=["POST"])
def edit_profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    bio = request.form.get("bio", "").strip()

    connection = get_db_connection()

    connection.execute(
        """
        UPDATE users
        SET bio = ?
        WHERE id = ?
        """,
        (bio, session["user_id"])
    )

    connection.commit()
    connection.close()

    return redirect(url_for("profile"))


@app.route("/upload-profile-photo", methods=["POST"])
def upload_profile_photo():

    if "user_id" not in session:
        return redirect(url_for("login"))

    file = request.files.get("profile_image")

    if file and file.filename:

        filename = secure_filename(file.filename)

        allowed_extensions = {
            "png",
            "jpg",
            "jpeg",
            "gif",
            "webp"
        }

        extension = filename.rsplit(".", 1)[-1].lower()

        if extension in allowed_extensions:

            upload_folder = os.path.join(
                app.static_folder,
                "images"
            )

            os.makedirs(upload_folder, exist_ok=True)

            new_filename = (
                "profile_"
                + str(session["user_id"])
                + "."
                + extension
            )

            file.save(
                os.path.join(
                    upload_folder,
                    new_filename
                )
            )

            connection = get_db_connection()

            connection.execute(
                """
                UPDATE users
                SET profile_image = ?
                WHERE id = ?
                """,
                (
                    new_filename,
                    session["user_id"]
                )
            )

            connection.commit()
            connection.close()

    return redirect(url_for("profile"))


@app.route("/liked-posts")
def liked_posts():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    posts = connection.execute(
        """
        SELECT
            posts.*,
            users.name,
            users.username
        FROM posts
        JOIN likes
        ON posts.id = likes.post_id
        JOIN users
        ON posts.user_id = users.id
        WHERE likes.user_id = ?
        ORDER BY likes.id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    connection.close()

    return render_template(
        "liked_posts.html",
        posts=posts
    )


@app.route("/save/<int:post_id>", methods=["POST"])
def save_post(post_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    existing = connection.execute(
        """
        SELECT *
        FROM saved_posts
        WHERE post_id = ?
        AND user_id = ?
        """,
        (
            post_id,
            session["user_id"]
        )
    ).fetchone()

    if existing:

        connection.execute(
            """
            DELETE FROM saved_posts
            WHERE post_id = ?
            AND user_id = ?
            """,
            (
                post_id,
                session["user_id"]
            )
        )

    else:

        connection.execute(
            """
            INSERT INTO saved_posts
            (post_id, user_id)
            VALUES (?, ?)
            """,
            (
                post_id,
                session["user_id"]
            )
        )

    connection.commit()
    connection.close()

    return redirect(request.referrer or url_for("home"))


@app.route("/saved-posts")
def saved_posts():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    posts = connection.execute(
        """
        SELECT
            posts.*,
            users.name,
            users.username
        FROM posts
        JOIN saved_posts
        ON posts.id = saved_posts.post_id
        JOIN users
        ON posts.user_id = users.id
        WHERE saved_posts.user_id = ?
        ORDER BY saved_posts.id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    connection.close()

    return render_template(
        "saved_posts.html",
        posts=posts
    )


# ==========================================
# CREATE POST
# ==========================================

@app.route("/create-post", methods=["GET", "POST"])
def create_post():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        content = request.form["content"].strip()

        image = request.files.get("image")

        image_filename = None

        if image and image.filename:

            filename = secure_filename(image.filename)

            allowed_extensions = {
                "png",
                "jpg",
                "jpeg",
                "gif",
                "webp"
            }

            extension = filename.rsplit(".", 1)[-1].lower()

            if extension in allowed_extensions:

                upload_folder = os.path.join(
                    app.static_folder,
                    "images"
                )

                os.makedirs(
                    upload_folder,
                    exist_ok=True
                )

                image_filename = (
                    "post_"
                    + str(session["user_id"])
                    + "_"
                    + filename
                )

                image.save(
                    os.path.join(
                        upload_folder,
                        image_filename
                    )
                )

        if content:

            connection = get_db_connection()

            connection.execute(
                """
                INSERT INTO posts
                (user_id, content, image)
                VALUES (?, ?, ?)
                """,
                (
                    session["user_id"],
                    content,
                    image_filename
                )
            )

            connection.commit()
            connection.close()

            return redirect(url_for("home"))

    return render_template("create_post.html")


# ==========================================
# USERS
# ==========================================

@app.route("/users")
def users():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    users = connection.execute(
        """
        SELECT
            id,
            name,
            username,
            bio,
            profile_image
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()

    following = connection.execute(
        """
        SELECT following_id
        FROM followers
        WHERE follower_id = ?
        """,
        (session["user_id"],)
    ).fetchall()

    following_ids = [
        row["following_id"]
        for row in following
    ]

    connection.close()

    return render_template(
        "users.html",
        users=users,
        following_ids=following_ids
    )


# ==========================================
# LIKE / UNLIKE POST
# ==========================================

@app.route("/like/<int:post_id>", methods=["POST"])
def like_post(post_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    # Get the post owner
    post = connection.execute(
        """
        SELECT user_id
        FROM posts
        WHERE id = ?
        """,
        (post_id,)
    ).fetchone()

    if not post:
        connection.close()
        return redirect(request.referrer or url_for("home"))

    # Check whether the user already liked the post
    existing_like = connection.execute(
        """
        SELECT *
        FROM likes
        WHERE post_id = ?
        AND user_id = ?
        """,
        (
            post_id,
            session["user_id"]
        )
    ).fetchone()

    if existing_like:

        # UNLIKE
        connection.execute(
            """
            DELETE FROM likes
            WHERE post_id = ?
            AND user_id = ?
            """,
            (
                post_id,
                session["user_id"]
            )
        )

    else:

        # LIKE
        connection.execute(
            """
            INSERT INTO likes
            (post_id, user_id)
            VALUES (?, ?)
            """,
            (
                post_id,
                session["user_id"]
            )
        )

        # Don't notify if liking your own post
        if post["user_id"] != session["user_id"]:

            sender = connection.execute(
                """
                SELECT name
                FROM users
                WHERE id = ?
                """,
                (session["user_id"],)
            ).fetchone()

            if sender:

                connection.execute(
                    """
                    INSERT INTO notifications
                    (
                        user_id,
                        sender_id,
                        type,
                        post_id,
                        message
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        post["user_id"],
                        session["user_id"],
                        "like",
                        post_id,
                        sender["name"] + " liked your post"
                    )
                )

    connection.commit()
    connection.close()

    return redirect(
        request.referrer or url_for("home")
    )


# ==========================================
# ADD COMMENT
# ==========================================

@app.route("/comment/<int:post_id>", methods=["POST"])
def add_comment(post_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    content = request.form["content"].strip()

    if not content:
        return redirect(request.referrer or url_for("home"))

    connection = get_db_connection()

    # Get the owner of the post
    post = connection.execute(
        """
        SELECT user_id
        FROM posts
        WHERE id = ?
        """,
        (post_id,)
    ).fetchone()

    if not post:
        connection.close()
        return redirect(request.referrer or url_for("home"))

    # Add comment
    connection.execute(
        """
        INSERT INTO comments
        (post_id, user_id, content)
        VALUES (?, ?, ?)
        """,
        (
            post_id,
            session["user_id"],
            content
        )
    )

    # Don't notify when commenting on your own post
    if post["user_id"] != session["user_id"]:

        sender = connection.execute(
            """
            SELECT name
            FROM users
            WHERE id = ?
            """,
            (session["user_id"],)
        ).fetchone()

        if sender:

            connection.execute(
                """
                INSERT INTO notifications
                (
                    user_id,
                    sender_id,
                    type,
                    post_id,
                    message
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    post["user_id"],
                    session["user_id"],
                    "comment",
                    post_id,
                    sender["name"] + " commented on your post"
                )
            )

    connection.commit()
    connection.close()

    return redirect(
        request.referrer or url_for("home")
    )


@app.route("/follow/<int:user_id>", methods=["POST"])
def follow_user(user_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    # Prevent following yourself
    if user_id == session["user_id"]:
        return redirect(request.referrer or url_for("users"))

    connection = get_db_connection()

    # Check if already following
    existing_follow = connection.execute(
        """
        SELECT *
        FROM followers
        WHERE follower_id = ?
        AND following_id = ?
        """,
        (
            session["user_id"],
            user_id
        )
    ).fetchone()

    if existing_follow:

        # UNFOLLOW
        connection.execute(
            """
            DELETE FROM followers
            WHERE follower_id = ?
            AND following_id = ?
            """,
            (
                session["user_id"],
                user_id
            )
        )

    else:

        # FOLLOW
        connection.execute(
            """
            INSERT INTO followers
            (follower_id, following_id)
            VALUES (?, ?)
            """,
            (
                session["user_id"],
                user_id
            )
        )

        # Get current user's name
        sender = connection.execute(
            """
            SELECT name
            FROM users
            WHERE id = ?
            """,
            (session["user_id"],)
        ).fetchone()

        if sender:

            connection.execute(
                """
                INSERT INTO notifications
                (
                    user_id,
                    sender_id,
                    type,
                    message
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    session["user_id"],
                    "follow",
                    sender["name"] + " started following you"
                )
            )

    connection.commit()
    connection.close()

    return redirect(
        request.referrer or url_for("users")
    )


@app.route("/user/<int:user_id>")
def view_user_profile(user_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    # Get the selected user
    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    if not user:
        connection.close()
        return redirect(url_for("users"))

    # Count posts
    post_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM posts
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    # Count followers
    follower_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM followers
        WHERE following_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    # Count following
    following_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM followers
        WHERE follower_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    # Check whether logged-in user follows this user
    existing_follow = connection.execute(
        """
        SELECT *
        FROM followers
        WHERE follower_id = ?
        AND following_id = ?
        """,
        (
            session["user_id"],
            user_id
        )
    ).fetchone()

    # Get selected user's posts
    posts = connection.execute(
        """
        SELECT
            posts.*,
            users.name,
            users.username
        FROM posts
        JOIN users
        ON posts.user_id = users.id
        WHERE posts.user_id = ?
        ORDER BY posts.id DESC
        """,
        (user_id,)
    ).fetchall()

    connection.close()

    return render_template(
        "user_profile.html",
        user=user,
        post_count=post_count,
        follower_count=follower_count,
        following_count=following_count,
        posts=posts,
        is_following=existing_follow is not None
    )


@app.route("/notifications")
def notifications():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    # Get all notifications
    notifications = connection.execute(
        """
        SELECT
            notifications.*,
            users.name,
            users.username
        FROM notifications
        JOIN users
        ON notifications.sender_id = users.id
        WHERE notifications.user_id = ?
        ORDER BY notifications.id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    # Mark all notifications as read
    connection.execute(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
        """,
        (session["user_id"],)
    )

    connection.commit()
    connection.close()

    return render_template(
        "notifications.html",
        notifications=notifications
    )



@app.route("/delete-post/<int:post_id>", methods=["POST"])
def delete_post(post_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    # Get the post
    post = connection.execute(
        """
        SELECT *
        FROM posts
        WHERE id = ?
        """,
        (post_id,)
    ).fetchone()

    if not post:
        connection.close()
        return redirect(request.referrer or url_for("home"))

    # Only the post owner can delete it
    if post["user_id"] != session["user_id"]:
        connection.close()
        return redirect(request.referrer or url_for("home"))

    # Delete related likes
    connection.execute(
        """
        DELETE FROM likes
        WHERE post_id = ?
        """,
        (post_id,)
    )

    # Delete related comments
    connection.execute(
        """
        DELETE FROM comments
        WHERE post_id = ?
        """,
        (post_id,)
    )

    # Delete related saved posts
    connection.execute(
        """
        DELETE FROM saved_posts
        WHERE post_id = ?
        """,
        (post_id,)
    )

    # Delete notifications related to this post
    connection.execute(
        """
        DELETE FROM notifications
        WHERE post_id = ?
        """,
        (post_id,)
    )

    # Delete the post
    connection.execute(
        """
        DELETE FROM posts
        WHERE id = ?
        """,
        (post_id,)
    )

    connection.commit()
    connection.close()

    # Delete uploaded image from the server
    if post["image"]:

        image_path = os.path.join(
            app.static_folder,
            "images",
            post["image"]
        )

        if os.path.exists(image_path):
            os.remove(image_path)

    return redirect(request.referrer or url_for("home"))


# ==========================================
# FOLLOWERS
# ==========================================

@app.route("/followers/<int:user_id>")
def followers(user_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    if not user:
        connection.close()
        return redirect(url_for("home"))

    followers = connection.execute(
        """
        SELECT
            users.id,
            users.name,
            users.username,
            users.bio,
            users.profile_image
        FROM followers
        JOIN users
        ON followers.follower_id = users.id
        WHERE followers.following_id = ?
        ORDER BY followers.id DESC
        """,
        (user_id,)
    ).fetchall()

    # Get users that the logged-in user already follows
    following = connection.execute(
        """
        SELECT following_id
        FROM followers
        WHERE follower_id = ?
        """,
        (session["user_id"],)
    ).fetchall()

    following_ids = [
        row["following_id"]
        for row in following
    ]

    connection.close()

    return render_template(
        "followers.html",
        user=user,
        followers=followers,
        following_ids=following_ids
    )


# ==========================================
# FOLLOWING
# ==========================================

@app.route("/following/<int:user_id>")
def following(user_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    if not user:
        connection.close()
        return redirect(url_for("home"))

    following = connection.execute(
        """
        SELECT
            users.id,
            users.name,
            users.username,
            users.bio,
            users.profile_image
        FROM followers
        JOIN users
        ON followers.following_id = users.id
        WHERE followers.follower_id = ?
        ORDER BY followers.id DESC
        """,
        (user_id,)
    ).fetchall()

    # Get users that the logged-in user already follows
    following_list = connection.execute(
        """
        SELECT following_id
        FROM followers
        WHERE follower_id = ?
        """,
        (session["user_id"],)
    ).fetchall()

    following_ids = [
        row["following_id"]
        for row in following_list
    ]

    connection.close()

    return render_template(
        "following.html",
        user=user,
        following=following,
        following_ids=following_ids
    )


# ==========================================
# SEARCH
# ==========================================

@app.route("/search")
def search():

    if "user_id" not in session:
        return redirect(url_for("login"))

    query = request.args.get("q", "").strip()

    connection = get_db_connection()

    users = []
    posts = []

    # Get users already followed by logged-in user
    following = connection.execute(
        """
        SELECT following_id
        FROM followers
        WHERE follower_id = ?
        """,
        (session["user_id"],)
    ).fetchall()

    following_ids = [
        row["following_id"]
        for row in following
    ]

    if query:

        users = connection.execute(
            """
            SELECT
                id,
                name,
                username,
                bio,
                profile_image
            FROM users
            WHERE name LIKE ?
               OR username LIKE ?
            ORDER BY name ASC
            """,
            (
                "%" + query + "%",
                "%" + query + "%"
            )
        ).fetchall()

        posts = connection.execute(
            """
            SELECT
                posts.*,
                users.name,
                users.username
            FROM posts
            JOIN users
            ON posts.user_id = users.id
            WHERE posts.content LIKE ?
            ORDER BY posts.id DESC
            """,
            (
                "%" + query + "%",
            )
        ).fetchall()

    connection.close()

    return render_template(
        "search.html",
        query=query,
        users=users,
        posts=posts,
        following_ids=following_ids
    )


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    app.run(debug=True)
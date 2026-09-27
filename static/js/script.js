/* =========================================
   CONNECTHUB JAVASCRIPT
========================================= */


/* LIKE POST */

function likePost(button) {

    if (button.classList.contains("liked")) {

        button.classList.remove("liked");

        button.innerHTML = "♡ Like";

    } else {

        button.classList.add("liked");

        button.innerHTML = "❤️ Liked";

    }

}


/* FOLLOW USER */

function followUser(button) {

    if (button.innerText === "Follow") {

        button.innerText = "Following";

        button.style.background = "#16a34a";

    } else {

        button.innerText = "Follow";

        button.style.background = "";

    }

}


/* SEARCH USERS AND POSTS */

function searchUsers() {

    const input = document.getElementById("searchInput");

    if (!input) {
        return;
    }

    const searchText = input.value.trim();

    if (searchText !== "") {

        window.location.href =
            "/search?q=" +
            encodeURIComponent(searchText);

    }

}


/* ENTER KEY SEARCH */

const searchInput =
    document.getElementById("searchInput");

if (searchInput) {

    searchInput.addEventListener(
        "keydown",
        function(event) {

            if (event.key === "Enter") {

                event.preventDefault();

                searchUsers();

            }

        }
    );

}

// =========================
// SHOW COMMENT BOX
// =========================

function showCommentBox(button) {

    const post = button.closest(".modern-post");

    if (!post) {
        return;
    }

    const commentsSection =
        post.querySelector(".comments-section");

    if (!commentsSection) {
        return;
    }

    commentsSection.classList.toggle("show");

    if (commentsSection.classList.contains("show")) {

        const input =
            commentsSection.querySelector("input");

        if (input) {
            input.focus();
        }
    }
}

// =========================
// SHARE POST
// =========================

function sharePost(postId) {

    const shareUrl =
        window.location.origin +
        "/#post-" +
        postId;


    // Use phone/browser share if available
    if (navigator.share) {

        navigator.share({
            title: "ConnectHub Post",
            text: "Check out this post on ConnectHub!",
            url: shareUrl
        });

    } else {

        // Copy link for desktop browsers
        navigator.clipboard.writeText(shareUrl)
            .then(function() {

                alert("Post link copied!");

            })
            .catch(function() {

                alert("Unable to copy the post link.");

            });

    }
}

// =========================
// SHOW / HIDE COMMENT BOX
// =========================

function showCommentBox(button) {

    const post = button.closest(".modern-post");

    if (!post) {
        return;
    }

    const commentBox =
        post.querySelector(".comment-box");

    if (!commentBox) {
        return;
    }

    commentBox.classList.toggle("show");


    if (commentBox.classList.contains("show")) {

        const input =
            commentBox.querySelector("input");

        if (input) {
            input.focus();
        }
    }
}
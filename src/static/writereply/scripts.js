const queryString = window.location.search
const params = new URLSearchParams(queryString)

const user = params.get("user")
const isPostParam = params.get("isPost")
const id = params.get("id")

function formatTimestamp(timestamp) {
    const date = new Date(timestamp * 1000);
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const month = monthNames[date.getUTCMonth()];
    const day = String(date.getUTCDate()).padStart(2, '0');
    const year = date.getUTCFullYear();
    const hours = String(date.getUTCHours()).padStart(2, '0');
    const minutes = String(date.getUTCMinutes()).padStart(2, '0');
    
    return `${month} ${day}, ${year}, ${hours}:${minutes}`;
  }

function newElement(tagName, attributes){
    const e = document.createElement(tagName)
    for (const key in attributes) {
        e.setAttribute(key, attributes[key])
    }
    return e
}

function createPostDiv(data, parent){
    const post = newElement("div", {"class": "submission"})
    parent.appendChild(post)

    const authorElement = newElement("p", {"class": "author"})
    authorElement.innerText = data.user
    post.appendChild(authorElement)

    const textElement = newElement("p", {"class": "text"})
    textElement.innerText = data.text
    post.appendChild(textElement)

    const dateElement = newElement("p", {"class": "date"})
    dateElement.innerText = formatTimestamp(data.posted_at)
    post.appendChild(dateElement)
}

if(user && isPostParam && id){
    const type = isPostParam == "true" ? "posts" : "comments"

    fetch(`/api/preview/${type}/${id}@${user}`)
        .then(response => response.json())
        .then(data => {
            createPostDiv(data, document.getElementById("parent-post"))
        })
}

function comment() {
    const commentTextArea = document.getElementById("text-content")
    const textContent = commentTextArea.value

    const body = {
        parent: {
            id: id,
            type: isPostParam == "true" ? "post" : "comment"
        },
        text: textContent
    }

    fetch(`/api/createcomment/`, {
            "method": "POST",
            "body": JSON.stringify(body),
            "headers": {
                "Content-Type": "application/json"
            }
        })
        .then(response => response.json())
        .then(data => {
            window.location.href = `/posts/${data.parent_post_id}`
        })
}
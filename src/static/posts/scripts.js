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

function createCommentsLookup(comments){
    const commentsLookup = {}
    for(const comment of comments){
        if(!(comment.parent.id in commentsLookup)){
            commentsLookup[comment.parent.id] = []
        }
        commentsLookup[comment.parent.id].push(comment)
    }
    return commentsLookup
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

function createReplyDivs(commentsLookup, parentId, parentElement){
    const repliesElement = newElement("div", {"class": "replies-container"})
    parentElement.appendChild(repliesElement)

    if(!(parentId in commentsLookup))
        return

    for(const comment of commentsLookup[parentId]){
        console.log(comment)
        createPostDiv(comment, repliesElement)
        createReplyDivs(commentsLookup, comment.id, repliesElement)
    }
}

const url = window.location.href;
const id = url.substring(url.lastIndexOf('/') + 1);

fetch(`/api/posts/${id}`)
  .then(response => response.json())
  .then(data => {
    const parent = document.getElementById("content")

    createPostDiv(data, parent)

    const commentsLookup = createCommentsLookup(data.comments)

    createReplyDivs(commentsLookup, data.id, parent)
})
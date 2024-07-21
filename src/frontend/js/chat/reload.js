let isLoading = false
let gotRequestWhileLoading = false

function reloadChat() {
    const messagesDiv = document.getElementById("messages-container");
    const url = new URL(window.location.href);
    url.searchParams.set("messages_only", "True");
    fetch(url.toString())
	    .then(response => {
	        return response.text();
	    })
	    .then(html => {
	        messagesDiv.outerHTML = html;
            const newMessagesDiv = document.getElementById("messages-container");
            newMessagesDiv.scrollTop = newMessagesDiv.scrollHeight;
            
            isLoading = false;
            if (gotRequestWhileLoading) {
                gotRequestWhileLoading = false
                console.log("reload again")
                reloadChat()
            }
        });
}

const ws = new WebSocket("ws://"+location.host+"/ws"+location.pathname);

ws.addEventListener("message", (event) => {
    if(isLoading) {
        gotRequestWhileLoading = true
        console.log("reload saved")
        return;
    }
    isLoading = true;
    reloadChat();
});

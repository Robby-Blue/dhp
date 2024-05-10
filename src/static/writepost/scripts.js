function post() {
    const postTextArea = document.getElementById("text-content")
    const textContent = postTextArea.value

    fetch(`/api/createpost/`, {
            "method": "POST",
            "body": JSON.stringify({"text": textContent}),
            "headers": {
                "Content-Type": "application/json"
            }
        })
        .then(response => response.json())
        .then(data => {
            window.location.href = `/posts/${data.id}`
        })
}
from frontend import *

def get_login_site():
    return render("Login",
        form({"id": "content", "action": "/login/", "method": "POST", "css": "login.css"},
            input({"type": "password", "name": "token"}),
            br(),
            input({"type": "submit", "value": "Login"})
        )
    )
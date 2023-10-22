from users import auth
from export import export


auteh = auth()
auteh.login([input('token $ ')])
exp = export(data=auteh.users)
exp.start()

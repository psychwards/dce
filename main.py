from users import auth
from export import export


if __name__ == "__main__":
  auteh = auth()
  auteh.login([input('token $ ')])
  exp = export(data=auteh.users)
  exp.start()

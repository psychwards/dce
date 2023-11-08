from users import auth
from export import export

def main():
  auteh = auth()
  auteh.login([input('token $ ')])
  exp = export(data=auteh.users)
  exp.start()


if __name__ == "__main__":
  main()
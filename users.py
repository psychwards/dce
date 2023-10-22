import httpx
import strings
from rich import print


class auth:
    def __init__(self) -> None:
        self.session = httpx.Client()
        self.users = []

    def info(self, token):
        return self.session.get(
            url=f"{strings.BASE}/users/@me", headers={"Authorization": token}
        ).json()

    def get_channels(self, token):
        channels = self.session.get(
            url=f"{strings.BASE}/users/@me/channels", headers={"Authorization": token}
        ).json()
        self.users.append(
            {
                "token": token,
                "channels": [
                    {
                        "id": channel["id"],
                        "file_name": f'dm{channel["id"]}.json',
                        "type": channel["type"],
                    }
                    for channel in channels
                    if channel["type"] in [1, 3]
                ],
            }
        )

    def login(self, tokens):
        for token in tokens:
            if (
                self.session.get(
                    url=f"{strings.BASE}/users/@me/billing/payment-sources",
                    headers={"Authorization": token},
                ).status_code
                == 200
            ):
                user = self.info(token)
                print(
                    f"[[bold pink1]+[/bold pink1]] [bold medium_purple1]logged into [bold pink1]{user['username']}#{user['discriminator']}[/bold pink1][/bold medium_purple1]"
                )
                print(
                    f"[[bold pink1]i[/bold pink1]] [bold medium_purple1]scraping channels for [bold pink1]{user['username']}#{user['discriminator']}[/bold pink1][/bold medium_purple1]"
                )
                self.get_channels(token)
                

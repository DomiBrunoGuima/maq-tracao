"""Senha do acesso desenvolvedor (AUTOMATIC): só o hash PBKDF2-SHA256.

Não edite à mão. Para definir ou trocar a senha, rode na raiz do repositório:

    python instalacao/definir_senha_desenvolvedor.py

e depois faça commit deste arquivo e um novo build. Vazio = login desativado.
"""

SENHA_HASH = "pbkdf2_sha256$200000$aebdd2c1b870554a24297b773659536e$b78204edd5dfa0813032793fcff2e312459733fd876e349c78949fccecb864d9"

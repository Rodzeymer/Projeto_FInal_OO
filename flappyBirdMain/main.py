import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pygame
import asyncio
import websockets
import assets
import configs
from objects.background import Background
from objects.bird import Bird
from objects.column import Column
from objects.floor import Floor
from objects.gameover_message import GameOverMessage
from objects.gamestart_message import GameStartMessage
from objects.score import Score

def cadastro():
    cadastro = "/content/cadastro.txt"
    with open(cadastro, "a") as f:
        nome = input("Digite seu nome: ")
        senha = input("Digite sua senha: ")
        # Escreve o nome e a senha no arquivo, separados por vírgula
        f.write(f"{nome},{senha}\n")
        f.close()
        print("Cadastro realizado com sucesso!")
        print("Agora você pode fazer login!")
        login()

def login():
    cadastro = "/content/cadastro.txt"
    # Ler o arquivo e criar um dicionário com nomes e senhas
    usuarios = {}
    try:
        with open(cadastro, "r") as f:
            for linha in f:
                # Remove o \n e divide a linha em nome e senha
                nome, senha = linha.strip().split(",")
                usuarios[nome] = senha
    except FileNotFoundError:
        print("Nenhum usuário cadastrado. Por favor, faça o cadastro primeiro.")
        return

    while True:
        nome = input("Digite seu nome: ")
        if nome in usuarios:
            senha = input("Digite sua senha: ")
            if senha == usuarios[nome]:
                print("Login realizado com sucesso!")
                break
            else:
                print("Senha incorreta! Tente novamente.")
        else:
            print("Nome de usuário incorreto! Tente novamente.")

# Pergunta ao usuário se é novo
entrando = input("Usuário novo? [S/N]").upper()
if entrando == "S":
    cadastro()
else:
    login()

pygame.init()

screen = pygame.display.set_mode((configs.SCREEN_WIDTH, configs.SCREEN_HEIGHT))
pygame.display.set_caption("Flappy Bird Game v1.0.2")

base_path = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(base_path, 'assets', 'icons', 'red_bird.png')
img = pygame.image.load(icon_path)
pygame.display.set_icon(img)

sprites_path = os.path.join(base_path, 'assets', 'sprites')

assets.load_sprites()



clock = pygame.time.Clock()
column_create_event = pygame.USEREVENT
running = True
gameover = False
gamestarted = False
logged_in = False  # Controla se o usuário está logado
current_user = None  # Armazena o usuário atual

assets.load_sprites()
assets.load_audios()

sprites = pygame.sprite.LayeredUpdates()

def create_sprites():
    Background(0, sprites)
    Background(1, sprites)
    Floor(0, sprites)
    Floor(1, sprites)
    return Bird(sprites), GameStartMessage(sprites), Score(sprites)

bird, game_start_message, score = create_sprites()

# Função para enviar mensagens ao servidor WebSocket
async def send_message(message):
    async with websockets.connect("ws://localhost:8765") as websocket:
        await websocket.send(message)
        response = await websocket.recv()
        print(response)
        return response

# Função para registrar um novo usuário
async def register(username, password):
    response = await send_message(f"register:{username}:{password}")
    return "register_success" in response

# Função para fazer login
async def login(username, password):
    response = await send_message(f"login:{username}:{password}")
    return "login_success" in response

# Função para fazer logout
async def logout():
    response = await send_message("logout:")
    return "logout_success" in response

async def main():
    global running, gameover, gamestarted, logged_in, current_user

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Verifica se o usuário está logado antes de permitir interações com o jogo
            if not logged_in:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:  # Registro
                        username = input("Digite um nome de usuário: ")
                        password = input("Digite uma senha: ")
                        if await register(username, password):
                            print("Registro bem-sucedido!")
                        else:
                            print("Falha no registro.")

                    elif event.key == pygame.K_l:  # Login
                        username = input("Digite seu nome de usuário: ")
                        password = input("Digite sua senha: ")
                        if await login(username, password):
                            logged_in = True
                            current_user = username
                            print(f"Login bem-sucedido! Bem-vindo, {username}!")
                        else:
                            print("Falha no login.")
            else:
                # Lógica do jogo (apenas se o usuário estiver logado)
                if event.type == column_create_event:
                    Column(sprites)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and not gamestarted and not gameover:
                        gamestarted = True
                        game_start_message.kill()
                        pygame.time.set_timer(column_create_event, 1500)
                    if event.key == pygame.K_ESCAPE and gameover:
                        gameover = False
                        gamestarted = False
                        sprites.empty()
                        bird, game_start_message, score = create_sprites()
                    if event.key == pygame.K_o:  # Logout
                        if await logout():
                            logged_in = False
                            current_user = None
                            print("Logout bem-sucedido!")

            # Manipulação de eventos do jogo (apenas se o usuário estiver logado e o jogo não estiver em gameover)
            if not gameover and logged_in:
                bird.handle_event(event)

        # Desenha os sprites na tela
        screen.fill(0)
        sprites.draw(screen)

        # Atualiza os sprites (apenas se o jogo estiver em andamento)
        if gamestarted and not gameover:
            sprites.update()

        # Verifica colisões
        if bird.check_collision(sprites) and not gameover:
            gameover = True
            gamestarted = False
            GameOverMessage(sprites)
            pygame.time.set_timer(column_create_event, 0)
            assets.play_audio("hit")

        # Atualiza a pontuação
        for sprite in sprites:
            if type(sprite) is Column and sprite.is_passed():
                score.value += 1
                assets.play_audio("point")

        # Atualiza a tela
        pygame.display.flip()
        clock.tick(configs.FPS)

    pygame.quit()

# Executa o loop principal do jogo com suporte a async/await
asyncio.run(main())

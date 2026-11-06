"""Simula o que o robô lê: estado verdadeiro da rua (luz e distância) e leituras com os defeitos dos sensores de verdade."""
import numpy as np

from caracteristicas import JANELA, caracteristicas

HZ = 10
PASSOS = 400  # 40 s por episódio
LDR_ESCURO, LDR_CLARO = 300, 3200  # contagens do ADC de referência


def trajetoria_luz(r):
    t = np.arange(PASSOS)
    tipo = r.choice(["escuro", "claro", "transicao", "piscando"], p=[0.25, 0.35, 0.15, 0.25])
    nivel = np.full(PASSOS, r.uniform(0, 0.28) if tipo == "escuro" else r.uniform(0.35, 1.0))
    piscando = np.zeros(PASSOS, bool)
    if tipo == "transicao":  # sombra ou lâmpada que liga e desliga, com rampa de 0,5 a 5 s
        for _ in range(r.integers(1, 3)):
            ini, rampa, novo = r.integers(20, PASSOS - 60), r.integers(5, 50), r.uniform(0, 1)
            nivel = np.where(t >= ini, nivel[ini] + (novo - nivel[ini]) * np.clip((t - ini) / rampa, 0, 1), nivel)
    if tipo == "piscando":  # lâmpada com defeito: alterna entre acesa e quase apagada em intervalos irregulares
        ini = r.integers(10, PASSOS - 200)
        fim = ini + r.integers(60, 200)
        alto = r.uniform(0.55, 0.95)
        baixo = alto * r.uniform(0.05, 0.4)
        estado, i = True, ini
        while i < fim:
            dur = r.integers(1, 7)
            nivel[i:min(i + dur, fim)] = alto if estado else baixo
            piscando[i:min(i + dur, fim)] = True
            estado, i = not estado, i + dur
    return nivel, piscando


def trajetoria_distancia(r):
    t = np.arange(PASSOS)
    tipo = r.choice(["longe", "perto", "aproxima", "aparece"], p=[0.35, 0.2, 0.35, 0.10])
    if tipo == "longe":
        dist = np.full(PASSOS, r.uniform(80, 200))
    elif tipo == "perto":
        dist = np.full(PASSOS, r.uniform(8, 60))
    elif tipo == "aparece":
        ini = r.integers(20, PASSOS - 60)
        dist = np.where(t >= ini, r.uniform(8, 60), r.uniform(80, 200))
    else:  # alguém ou algo vem na direção do robô, para perto e depois vai embora; repete várias vezes
        dist = np.full(PASSOS, r.uniform(100, 200))
        i = r.integers(5, 40)
        while i < PASSOS - 20:
            inicio, fim, v = r.uniform(100, 200), r.uniform(3, 40), r.uniform(25, 150) / HZ
            dur = int((inicio - fim) / v) + 1
            fim_passo = min(PASSOS, i + dur + r.integers(5, 25))
            for k in range(i, fim_passo):
                dist[k] = max(fim, inicio - v * (k - i))
            i = fim_passo + r.integers(5, 30)
            if i < PASSOS:
                dist[i:] = r.uniform(100, 200)
    return np.clip(dist, 3, 200)


def rotular(luz, dist, piscando):
    vel = -np.gradient(dist) * HZ  # cm/s se aproximando
    vel = np.convolve(vel, np.ones(5) / 5, mode="same")
    r = np.zeros(PASSOS, int)
    r[luz < 0.30] = 1
    r[piscando] = 4
    r[(vel > 40) & (dist < 100)] = 5
    r[(dist < 30) & (luz >= 0.30)] = 2
    r[(dist < 30) & (luz < 0.30)] = 3
    return r


def medir(luz, dist, r, ruido=1.0):
    """Leituras com defeitos: ruído, calibração do LDR um pouco errada e o HC-SR04 que às vezes não ouve eco ou mente."""
    cal_esc, cal_cla = LDR_ESCURO * (1 + r.normal(0, 0.08)), LDR_CLARO * (1 + r.normal(0, 0.08))
    contagem = LDR_ESCURO + (LDR_CLARO - LDR_ESCURO) * luz ** 0.8 + r.normal(0, 45 * ruido, PASSOS) + r.normal(0, 0.03 * luz * 2900 * ruido, PASSOS)
    luz_lida = np.clip((contagem - cal_esc) / (cal_cla - cal_esc), 0, 1)
    dist_lida = dist + r.normal(0, (0.4 + 0.006 * dist) * ruido, PASSOS)
    sem_eco = r.random(PASSOS) < (0.02 + 0.08 * (dist > 150)) * ruido
    mentira = r.random(PASSOS) < 0.02 * ruido
    dist_lida = np.where(sem_eco, 200, np.where(mentira, r.uniform(2, 40, PASSOS), dist_lida))
    return luz_lida, np.clip(dist_lida, 2, 200)


def leituras(semente, ruido=1.0):
    """Uma sequência de leituras (como o robô veria) e a classe verdadeira de cada instante."""
    r = np.random.default_rng(semente)
    luz, piscando = trajetoria_luz(r)
    dist = trajetoria_distancia(r)
    classe = rotular(luz, dist, piscando)
    luz_lida, dist_lida = medir(luz, dist, r, ruido)
    return luz_lida, dist_lida, classe


def episodio(semente, ruido=1.0, passo_janela=4):
    r = np.random.default_rng(semente)
    luz, piscando = trajetoria_luz(r)
    dist = trajetoria_distancia(r)
    classe = rotular(luz, dist, piscando)
    luz_lida, dist_lida = medir(luz, dist, r, ruido)
    X, y, brutas = [], [], []
    for t in range(JANELA - 1, PASSOS, passo_janela):
        jl, jd = luz_lida[t - JANELA + 1:t + 1], dist_lida[t - JANELA + 1:t + 1]
        X.append(caracteristicas(jl, jd))
        y.append(classe[t])
        brutas.append(np.concatenate([jl, jd]))
    return np.array(X), np.array(y), np.array(brutas)


def conjunto(sementes, ruido=1.0):
    """ruido=None sorteia, para cada episódio, um nível de 0,5 a 3 vezes o ruído previsto (aumento de dados)."""
    sorteio = lambda s: np.random.default_rng(10_000 + s).choice([0.5, 1.0, 1.5, 2.0, 3.0]) if ruido is None else ruido
    partes = [episodio(s, sorteio(s)) for s in sementes]
    return np.vstack([p[0] for p in partes]), np.concatenate([p[1] for p in partes]), np.vstack([p[2] for p in partes])

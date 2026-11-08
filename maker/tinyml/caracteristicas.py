"""Características calculadas sobre uma janela de 8 leituras (0,8 s a 10 leituras por segundo).
A mesma conta existe em C++ (robo/caracteristicas.h); o testar_c.py confere que as duas dão o mesmo resultado."""
import numpy as np

JANELA = 8
PASSO_S = 0.1  # uma leitura a cada 100 ms
CLASSES = ["ok", "pouca_luz", "obstaculo", "escuro_e_obstaculo", "luz_piscando", "objeto_se_aproximando"]


def caracteristicas(luz, dist):
    """luz: 8 valores de 0 a 1; dist: 8 valores em cm. Devolve as 5 entradas do modelo, todas em escala de uns 0 a 1."""
    luz, dist = np.asarray(luz, float), np.asarray(dist, float)
    metade = JANELA // 2
    tendencia = (np.median(dist[metade:]) - np.median(dist[:metade])) / (metade * PASSO_S)  # cm/s, negativo = aproximando
    return np.array([luz.mean(), 3 * luz.std(), luz.max() - luz.min(), np.median(dist) / 200, tendencia / 100])

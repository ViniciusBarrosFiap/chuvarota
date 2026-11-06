NOMES = ["nível 1 (0 a 20 cm)", "nível 2 (20 a 45 cm)", "nível 3 (45 a 100 cm)", "nível 4 (mais de 100 cm)"]
CORES = [(80, 200, 80), (0, 200, 255), (0, 120, 255), (0, 0, 230)]  # BGR


def alerta(nivel):
    if nivel == 0:
        return "Atenção: água na roda do ônibus. Reduza a velocidade."
    if nivel == 1:
        return "Perigo: não atravesse de carro."
    return "Perigo extremo: não atravesse e procure um local alto."

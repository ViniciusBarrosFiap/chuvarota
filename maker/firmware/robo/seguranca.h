// Filtro da leitura de distância, sem dependência do Arduino (testado no computador em maker/tinyml/testar_seguranca.py).
#pragma once

// O HC-SR04 devolve "sem eco" (200) quando não há nada à frente, mas também quando o obstáculo está perto demais (menos de uns
// 2 cm) ou é uma parede em ângulo que desvia o som. Se a leitura anterior era perto e agora ficou sem eco, o mais seguro é achar
// que o obstáculo continua ali, e não que o caminho abriu.
struct FiltroDistancia {
  enum { MAX_SEM_ECO = 20 };  // por no máximo 20 leituras (2 s); depois disso vale o "sem eco"
  float ultima = 200;         // última leitura com eco
  int sem_eco = 0;            // quantas leituras "sem eco" seguidas foram trocadas por "obstáculo colado"

  // d: leitura nova (200 = sem eco). perto_cm: abaixo disso a leitura anterior conta como "perto".
  // colado_cm: valor devolvido quando um "sem eco" é trocado por obstáculo (deve ser menor que a distância de parada).
  float filtrar(float d, float perto_cm, float colado_cm) {
    if (d >= 200 && ultima < perto_cm && sem_eco < MAX_SEM_ECO) {
      sem_eco++;
      return colado_cm;
    }
    sem_eco = 0;
    ultima = d;
    return d;
  }

  // depois de uma manobra as leituras de antes não valem mais
  void esquecer() {
    ultima = 200;
    sem_eco = 0;
  }
};

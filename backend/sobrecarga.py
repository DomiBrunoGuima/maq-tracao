"""Proteção de sobrecarga da célula de carga.

Cada leitura de força (status do Controle/Flexão e streams de aquisição) passa por
:meth:`MonitorSobrecarga.verificar`. Se o módulo da força atingir o limite
configurado (``sobrecarga_limite_kgf``), o monitor dispara o pulso de parada e
trava o alarme até o operador reconhecer. Enquanto a força continuar acima do
limite, o pulso é repetido a cada ``REPETIR_PULSO_S`` segundos.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Callable

N_POR_KGF = 9.80665
REPETIR_PULSO_S = 2.0


class MonitorSobrecarga:
    def __init__(self, get_config: Callable[[], dict], agora: Callable[[], float] = time.monotonic) -> None:
        self._get_config = get_config
        self._agora = agora
        self._lock = threading.Lock()
        self._ultimo_pulso: float | None = None
        self._estado: dict = self._estado_vazio()

    @staticmethod
    def _estado_vazio() -> dict:
        return {
            "ativo": False, "forca_kgf": None, "forca_max_kgf": None, "limite_kgf": None,
            "quando": None, "origem": None, "pulso_enviado": False, "pulsos": 0, "erro": None,
        }

    def limite_kgf(self) -> float | None:
        """Limite em kgf, ou None quando a proteção está desligada."""
        cfg = self._get_config()
        if not cfg.get("sobrecarga_ativa"):
            return None
        try:
            lim = float(cfg.get("sobrecarga_limite_kgf") or 0)
        except (TypeError, ValueError):
            return None
        return lim if lim > 0 else None

    def estado(self) -> dict:
        with self._lock:
            return {**self._estado, "limite_config_kgf": self.limite_kgf()}

    def reconhecer(self) -> dict:
        with self._lock:
            self._estado = self._estado_vazio()
            self._ultimo_pulso = None
        return self.estado()

    def verificar(self, forca_n: float | None, enviar_parada: Callable[[], None], origem: str = "tracao") -> bool:
        """Confere uma leitura de força (em N). Retorna True se ela está em sobrecarga
        (e, nesse caso, já mandou o pulso de parada, salvo se mandou há pouco)."""
        lim = self.limite_kgf()
        if lim is None or forca_n is None:
            return False
        forca_kgf = abs(float(forca_n)) / N_POR_KGF
        if forca_kgf < lim:
            return False

        with self._lock:
            agora = self._agora()
            novo = not self._estado["ativo"]
            if novo:
                self._estado.update({
                    "ativo": True, "limite_kgf": lim, "origem": origem,
                    "quando": datetime.now().isoformat(timespec="seconds"),
                })
            self._estado["forca_kgf"] = round(forca_kgf, 3)
            anterior = self._estado["forca_max_kgf"] or 0.0
            self._estado["forca_max_kgf"] = round(max(anterior, forca_kgf), 3)
            pulsar = self._ultimo_pulso is None or (agora - self._ultimo_pulso) >= REPETIR_PULSO_S
            if pulsar:
                self._ultimo_pulso = agora

        if pulsar:
            try:
                enviar_parada()
                erro = None
            except Exception as exc:  # o alarme continua valendo mesmo se o pulso falhar
                erro = str(exc) or exc.__class__.__name__
            with self._lock:
                if erro is None:
                    self._estado["pulso_enviado"] = True
                    self._estado["pulsos"] += 1
                self._estado["erro"] = erro
            print(f"[sobrecarga] {forca_kgf:.2f} kgf >= {lim:.2f} kgf ({origem}): "
                  f"{'pulso de parada enviado' if erro is None else 'FALHA no pulso: ' + erro}", flush=True)
        return True

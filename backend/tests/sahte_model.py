"""Senaryolu model istemcisi. Ağ çağrısı yapmaz."""

import json


class _Parca:
    def __init__(self, **alanlar: object) -> None:
        for anahtar, deger in alanlar.items():
            setattr(self, anahtar, deger)


class SahteIstemci:
    """Adımlar sırayla tüketilir. Metin düz yazıdır, liste bir veya daha çok run_sql'dir."""

    def __init__(self, adimlar: list) -> None:
        self.adimlar = list(adimlar)
        self.cagrilar: list[dict] = []

    @property
    def messages(self):
        return self

    def create(self, **kwargs):
        self.cagrilar.append(json.loads(json.dumps(kwargs, default=str)))
        adim = self.adimlar.pop(0) if self.adimlar else ""
        if isinstance(adim, str):
            icerik = [_Parca(type="text", text=adim)]
        else:
            sorgular = list(adim)
            icerik = [
                _Parca(
                    type="tool_use",
                    id=f"arac-{n}",
                    name="run_sql",
                    input={"sql": sql},
                )
                for n, sql in enumerate(sorgular, start=1)
            ]
        return _Parca(content=icerik)


def bagla(monkeypatch, adimlar: list) -> SahteIstemci:
    istemci = SahteIstemci(adimlar)
    monkeypatch.setattr("backend.app.api.query._model_istemcisi", lambda: istemci)
    return istemci

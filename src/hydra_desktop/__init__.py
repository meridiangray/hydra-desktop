"""The desktop app (apps layer, above hydra): `app` (window, proxy, routes; `main`), `home` (welcome screen), `look`,
`new`, `picker`, `profile`, `progress`. `hydra-desktop` runs `hydra_desktop.app:main`, and `python -m hydra_desktop`
runs it through `__main__`. Nothing is imported here, so `python -m hydra_desktop.picker` loads none of the app."""

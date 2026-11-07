# SimplyFeu pour Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Validate](https://github.com/VOTRE_UTILISATEUR/ha-simplyfeu/actions/workflows/validate.yml/badge.svg)](https://github.com/VOTRE_UTILISATEUR/ha-simplyfeu/actions/workflows/validate.yml)

Intégration personnalisée qui suit le prix d'un produit [SimplyFeu](https://www.simplyfeu.com)
(palette de granulés, bûches compressées…) et vous aide à commander au meilleur moment.

## Fonctionnalités

- Configuration entièrement par l'interface (aucun YAML).
- Un appareil par produit suivi, avec deux capteurs :
  - **Prix** : prix actuel, avec l'historique long terme de Home Assistant (graphiques, statistiques).
    Attributs : `product_name`, `previous_price`, `last_change`.
  - **Prix le plus bas** : plus bas prix jamais relevé, avec sa `date`.
- Événement `simplyfeu_price_changed` à chaque changement de prix, pour vos automatisations.
- Intervalle de relevé réglable (1 à 48 h, 6 h par défaut).
- Regex de prix et en-tête Cookie optionnels, pour les cas particuliers.

## Installation

### Via HACS (dépôt personnalisé)

1. HACS → menu ⋮ → **Dépôts personnalisés**.
2. URL : `https://github.com/VOTRE_UTILISATEUR/ha-simplyfeu`, catégorie **Intégration**.
3. Installez **SimplyFeu**, puis redémarrez Home Assistant.

### Manuelle

Copiez `custom_components/simplyfeu` dans le dossier `config/custom_components/` puis redémarrez.

## Configuration

**Paramètres → Appareils et services → Ajouter une intégration → SimplyFeu**, puis collez l'URL de la
page produit. Ajoutez une entrée par produit à suivre.

### Prix par commune

Les tarifs SimplyFeu dépendent de la commune de livraison. Si le prix relevé ne correspond pas à celui
que vous voyez dans votre navigateur :

1. Ouvrez la page produit et choisissez votre commune.
2. Outils de développement (F12) → **Réseau** → rechargez la page → cliquez sur la première requête.
3. Copiez la valeur de l'en-tête de requête **Cookie** et collez-la dans les options de l'intégration.

Le cookie peut expirer : si le prix redevient incohérent, recommencez l'opération.

### Prix non détecté

L'intégration cherche le prix dans le JSON-LD, les balises `itemprop="price"` et les éléments
`oe_currency_value` (sites Odoo). Si la page change, indiquez une regex Python contenant un groupe
nommé `p`, par exemple :

```
class="oe_price"[^>]*>\s*<span class="oe_currency_value">(?P<p>[\d\s,.]+)</span>
```

## Exemple d'automatisation

Notification quand le prix baisse, en précisant s'il s'agit d'un nouveau plus bas :

```yaml
automation:
  - alias: "Granulés : le prix baisse"
    trigger:
      - platform: event
        event_type: simplyfeu_price_changed
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.new_price < trigger.event.data.old_price }}"
    action:
      - service: notify.mobile_app_mon_telephone
        data:
          title: "🔥 {{ trigger.event.data.name }}"
          message: >
            {{ trigger.event.data.old_price }} € → {{ trigger.event.data.new_price }} €
            {% if trigger.event.data.is_new_low %}(plus bas jamais vu !){% endif %}
          data:
            url: "{{ trigger.event.data.url }}"
```

Données de l'événement : `entry_id`, `name`, `url`, `old_price`, `new_price`, `lowest_price`,
`is_new_low`.

## Développement

```bash
pip install pytest
pytest -q
```

La CI GitHub exécute `hassfest`, la validation HACS et les tests du parseur.

## Avertissement

Projet non officiel, sans lien avec SimplyFeu. L'intégration lit une page publique à intervalle
raisonnable ; ne descendez pas sous quelques heures pour ne pas surcharger le site.

## Licence

MIT

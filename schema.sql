-- ============================================================
-- ANNUAIRE QUARTIER — Schéma PostgreSQL
-- ============================================================
-- Hiérarchie : commune → quartier → menage → membre
-- À exécuter sur une base vide :
--     psql -U postgres -d annuaire_quartier -f schema.sql
-- ============================================================

-- Nettoyage si on relance le script (ordre inverse pour respecter les FK)
DROP TABLE IF EXISTS membre CASCADE;
DROP TABLE IF EXISTS menage CASCADE;
DROP TABLE IF EXISTS quartier CASCADE;
DROP TABLE IF EXISTS commune CASCADE;

-- ============================================================
-- TABLE COMMUNE
-- ============================================================
CREATE TABLE commune (
    id_commune     SERIAL PRIMARY KEY,
    nom            VARCHAR(80)  NOT NULL UNIQUE,
    slug           VARCHAR(40)  NOT NULL UNIQUE,
    type           VARCHAR(40)  NOT NULL DEFAULT 'commune_urbaine',
                                -- 'commune_urbaine' | 'sous_prefecture'
    population_osm INTEGER      DEFAULT 0,
    centroid_lat   DECIMAL(9,6),
    centroid_lng   DECIMAL(9,6)
);

CREATE INDEX idx_commune_slug ON commune(slug);

-- ============================================================
-- TABLE QUARTIER
-- ============================================================
CREATE TABLE quartier (
    id_quartier    SERIAL PRIMARY KEY,
    nom            VARCHAR(80)  NOT NULL,
    id_commune     INTEGER      NOT NULL REFERENCES commune(id_commune) ON DELETE CASCADE,
    lat            DECIMAL(9,6),
    lng            DECIMAL(9,6),
    UNIQUE (nom, id_commune)
);

CREATE INDEX idx_quartier_commune ON quartier(id_commune);

-- ============================================================
-- TABLE MENAGE
-- ============================================================
CREATE TABLE menage (
    id_menage         SERIAL PRIMARY KEY,
    nom_menage        VARCHAR(120) NOT NULL,
    id_commune        INTEGER      NOT NULL REFERENCES commune(id_commune)  ON DELETE RESTRICT,
    id_quartier       INTEGER      REFERENCES quartier(id_quartier) ON DELETE SET NULL,
    quartier_nom      VARCHAR(80)  NOT NULL,  -- redondance pratique (évite un JOIN à chaque liste)
    -- Logement
    type_logement     VARCHAR(40)  DEFAULT '',
    statut_occupation VARCHAR(40)  DEFAULT '',
    nombre_pieces     INTEGER      DEFAULT 0,
    -- Services de base
    source_eau        VARCHAR(40)  DEFAULT '',
    type_toilettes    VARCHAR(40)  DEFAULT '',
    source_eclairage  VARCHAR(40)  DEFAULT '',
    gestion_ordures   VARCHAR(40)  DEFAULT '',
    -- Biens durables (tableau Postgres natif)
    biens_durables    TEXT[]       DEFAULT ARRAY[]::TEXT[],
    -- Date du recensement
    date_recensement  DATE,
    -- Horodatage
    cree_le           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_menage_commune  ON menage(id_commune);
CREATE INDEX idx_menage_quartier ON menage(id_quartier);
CREATE INDEX idx_menage_nom      ON menage(LOWER(nom_menage));

-- ============================================================
-- TABLE MEMBRE
-- ============================================================
CREATE TABLE membre (
    id_membre              SERIAL PRIMARY KEY,
    id_menage              INTEGER     NOT NULL REFERENCES menage(id_menage) ON DELETE CASCADE,
    -- État civil
    prenom                 VARCHAR(60) NOT NULL,
    nom                    VARCHAR(60) NOT NULL,
    sexe                   VARCHAR(10) NOT NULL,    -- 'Masculin' | 'Féminin'
    date_naissance         DATE        NOT NULL,
    lien_chef              VARCHAR(40) DEFAULT '',
    situation_matrimoniale VARCHAR(40) DEFAULT 'Célibataire',
    -- Éducation
    niveau_instruction     VARCHAR(40) DEFAULT 'Aucun',
    sait_lire_ecrire       VARCHAR(10) DEFAULT 'Non',
    -- Activité économique
    situation_activite     VARCHAR(40) DEFAULT 'Inactif',
    type_emploi            VARCHAR(40) DEFAULT '',
    secteur_emploi         VARCHAR(40) DEFAULT '',
    -- Documents et santé
    piece_identite         VARCHAR(40) DEFAULT 'Aucune',
    handicap               VARCHAR(40) DEFAULT 'Aucun'
);

CREATE INDEX idx_membre_menage ON membre(id_menage);
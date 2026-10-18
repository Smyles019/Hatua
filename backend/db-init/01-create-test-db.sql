-- Runs once, the first time the container starts with an empty volume.
-- Tests use their own database so they never touch development data.
CREATE DATABASE hatua_test OWNER hatua;

#!/usr/bin/env node
/**
 * Construit la version « Artifact » de l'application à partir de index.html.
 *
 * Un Artifact fournit lui-même le squelette <!doctype html><head></head><body>,
 * donc la page publiée ne doit contenir ni doctype, ni <html>, ni <head>, ni <body>.
 * Ce script garde index.html comme source unique et n'en dérive que l'emballage :
 * même CSS, même JS, même comportement.
 *
 *   node build-artifact.js
 */
const fs = require('fs');
const path = require('path');

const SRC = path.join(__dirname, 'index.html');
const OUT = path.join(__dirname, 'artifact', 'atelier-diagnostic.html');
const TITRE = 'Atelier Diagnostic';

const src = fs.readFileSync(SRC, 'utf8');

const pick = (re, quoi) => {
  const m = src.match(re);
  if (!m) throw new Error('Section introuvable dans index.html : ' + quoi);
  return m;
};

const fonts = pick(/<link rel="preconnect"[\s\S]*?display=swap">/, 'liens de polices')[0];
const style = pick(/<style>[\s\S]*?<\/style>/, 'feuille de style')[0];
const body  = pick(/<body>\s*([\s\S]*?)\s*<\/body>/, 'contenu de la page')[1];

const out = [
  '<title>' + TITRE + '</title>',
  fonts,
  style,
  '',
  body,
  ''
].join('\n');

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, out);

const interdits = /<!doctype|<html[\s>]|<\/html>|<head[\s>]|<body[\s>]/i;
if (interdits.test(out)) throw new Error('La sortie contient encore des balises de squelette.');

console.log('→ ' + path.relative(__dirname, OUT) + ' (' + Math.round(out.length / 1024) + ' Ko)');

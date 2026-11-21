'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
require('../static/formatters.js');

const {formatDateTimeBR, languageLabel, sourceLabel} = globalThis.BibliotecaFormatters;

test('datas ISO com offset e UTC representam o mesmo minuto em São Paulo', () => {
  assert.equal(formatDateTimeBR('2026-11-21T14:39:12.786282-03:00'), '21/11/2026 às 14:39');
  assert.equal(formatDateTimeBR('2026-11-21T17:39:12Z'), '21/11/2026 às 14:39');
});

test('data com microssegundos omite segundos sem perder o fuso correto', () => {
  assert.equal(formatDateTimeBR('2026-11-21T17:39:59.999999+00:00'), '21/11/2026 às 14:39');
});

test('datas ausentes e inválidas recebem texto seguro', () => {
  for (const value of [null, undefined, '', 'not-a-date', 'Invalid Date', '2026-13-90']) {
    assert.equal(formatDateTimeBR(value), 'Não informado');
  }
});

test('códigos de idioma e catálogo conhecidos recebem rótulos amigáveis', () => {
  assert.equal(languageLabel('spa'), 'Espanhol');
  assert.equal(languageLabel('por'), 'Português');
  assert.equal(languageLabel('eng'), 'Inglês');
  assert.equal(languageLabel('fre'), 'Francês');
  assert.equal(languageLabel('fra'), 'Francês');
  assert.equal(sourceLabel('openlibrary'), 'Open Library');
  assert.equal(sourceLabel('google_books'), 'Google Books');
  assert.equal(languageLabel('xyz'), 'xyz');
  assert.equal(sourceLabel('catalogo-desconhecido'), 'catalogo-desconhecido');
});

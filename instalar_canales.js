import fs from 'fs';
import csv from 'csv-parser';
import mysql from 'mysql2/promise';

const DB_CONFIG = {
  host: 'localhost',
  user: 'iptv-user',
  password: 'S3cureP@ssw0rd', // Cambia esto por tu contraseña real si es distinta
  database: 'iptv_db',
};

const categoriasMap = new Map();
let categoriasCreadas = 0;
let canalesInsertados = 0;

async function cargarCategoriasYCanales() {
  const connection = await mysql.createConnection(DB_CONFIG);
  console.log("✅ Conectado a la base de datos.");

  const canales = [];

  // Leer todo el CSV primero
  await new Promise((resolve, reject) => {
    fs.createReadStream('canales_completos_procesados.csv')
      .pipe(csv())
      .on('data', (row) => canales.push(row))
      .on('end', resolve)
      .on('error', reject);
  });

  for (const row of canales) {
    const { nombre, url, formato, logo, estado, categoria } = row;

    try {
      let categoria_id;

      if (categoriasMap.has(categoria)) {
        categoria_id = categoriasMap.get(categoria);
      } else {
        const [rows] = await connection.execute('SELECT id FROM categorias WHERE nombre = ?', [categoria]);
        if (rows.length > 0) {
          categoria_id = rows[0].id;
        } else {
          const [result] = await connection.execute('INSERT INTO categorias (nombre) VALUES (?)', [categoria]);
          categoria_id = result.insertId;
          categoriasCreadas++;
          console.log(`🆕 Categoría creada: ${categoria}`);
        }
        categoriasMap.set(categoria, categoria_id);
      }

      await connection.execute(
        'INSERT INTO canales (nombre, url, formato, logo, estado, categoria_id) VALUES (?, ?, ?, ?, ?, ?)',
        [nombre, url, formato, logo || null, parseInt(estado), categoria_id]
      );
      canalesInsertados++;
      console.log(`✅ Canal insertado: ${nombre}`);
    } catch (err) {
      console.error(`❌ Error insertando canal ${nombre}:`, err.message);
    }
  }

  await connection.end();
  console.log('✅ Proceso finalizado.');
  console.log(`📂 Categorías creadas: ${categoriasCreadas}`);
  console.log(`📺 Canales insertados: ${canalesInsertados}`);
}

cargarCategoriasYCanales();

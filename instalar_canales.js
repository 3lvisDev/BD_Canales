import fs from 'fs';
import csv from 'csv-parser';
import mysql from 'mysql2/promise';

const DB_CONFIG = {
  host: 'localhost',
  user: 'root',
  password: '',  // <- Poner contraseña si aplica
  database: 'iptv_db'
};

const categoriasMap = new Map();
let categoriasCreadas = 0;
let canalesInsertados = 0;

async function cargarCategoriasYCanales() {
  const connection = await mysql.createConnection(DB_CONFIG);

  console.log("✅ Conectado a la base de datos.");

  // Leer CSV
  fs.createReadStream('canales_procesados.csv')
    .pipe(csv())
    .on('data', async (row) => {
      const { nombre, url, formato, logo, estado, categoria } = row;

      try {
        let categoria_id;

        if (categoriasMap.has(categoria)) {
          categoria_id = categoriasMap.get(categoria);
        } else {
          // Ver si existe en BD
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

        // Insertar canal
        await connection.execute(
          'INSERT INTO canales (nombre, url, formato, logo, estado, categoria_id) VALUES (?, ?, ?, ?, ?, ?)',
          [nombre, url, formato, logo || null, parseInt(estado), categoria_id]
        );
        canalesInsertados++;
      } catch (err) {
        console.error(`❌ Error insertando canal ${row.nombre}:`, err.message);
      }
    })
    .on('end', () => {
      console.log(`✅ Proceso finalizado.`);
      console.log(`📂 Categorías creadas: ${categoriasCreadas}`);
      console.log(`📺 Canales insertados: ${canalesInsertados}`);
      connection.end();
    });
}

cargarCategoriasYCanales();
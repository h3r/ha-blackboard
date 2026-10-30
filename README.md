# 🛒 Cesta Compartida para Home Assistant

Una integración y panel moderno para **Home Assistant** que transforma la gestión de la compra en el hogar en una experiencia fluida, colaborativa e inteligente.

[![HACS Custom Component](https://img.shields.io/badge/HACS-Custom_Repo-orange.svg?style=for-the-badge)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-41BDF5.svg?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io)

---

## ✨ Características principales

* 🚀 **100% Nativo en Home Assistant:** Sin necesidad de Docker externo, Node.js ni configuraciones de puertos. Se instala y actualiza directamente desde **HACS**.
* 📱 **Pestaña en el menú lateral:** Panel táctil moderno con soporte para modo oscuro/claro, animaciones fluidas y gestos de deslizar (*swipe*) para tachar o eliminar.
* 📦 **Sincronización con Home Assistant To-Do:** Cada lista genera una entidad nativa `todo.*` (por ejemplo, `todo.cesta_casa`). Compatible con **Google Assistant, Alexa, Siri y Assist** para añadir productos por voz.
* 📷 **Escáner de código de barras:** Reconocimiento instantáneo de productos alimentarios y marcas a través de **Open Food Facts** y catálogo local personalizado.
* 🪄 **OCR con IA (Gemini Vision):** Fotografía una lista manuscrita en un papel o una receta y la IA extraerá y categorizará automáticamente todos los productos con sus cantidades.
* 🔄 **Listas compartidas por código:** Comparte listas mediante códigos simples (`casa`, `compra-semanal`) o códigos QR para familiares y compañeros de piso.
* 🏷️ **Categorización automática en español:** Organiza los productos por pasillos del supermercado (Fruta y Verdura, Lácteos, Panadería, Limpieza, etc.).

---

## 📦 Instalación

### Método 1: A través de HACS (Recomendado)

1. Abre **HACS** en tu Home Assistant.
2. Ve a los tres puntos de la esquina superior derecha y selecciona **Repositorios personalizados**.
3. Añade la URL de este repositorio:
   ```text
   https://github.com/vpez/ha-cesta-compartida
   ```
4. Selecciona la categoría **Integración** (*Integration*) y pulsa **Añadir**.
5. Busca **Cesta Compartida**, pulsa **Descargar** y reinicia Home Assistant cuando se te solicite.

### Método 2: Instalación manual

1. Descarga el repositorio o la última *release*.
2. Copia la carpeta `custom_components/cesta_compartida/` en tu directorio `custom_components/` de Home Assistant.
3. Reinicia Home Assistant.

---

## ⚙️ Configuración

1. En Home Assistant, ve a **Ajustes** > **Dispositivos y servicios** > **Añadir integración**.
2. Busca **Cesta Compartida**.
3. Introduce:
   * **Nombre de la lista predeterminada** (por defecto: `casa`).
   * **Clave de API de Gemini** *(opcional, necesaria solo para el escaneo de listas manuscritas con IA)*.
4. Pulsa **Enviar**. Verás aparecer automáticamente **Cesta Compartida** en el menú lateral de Home Assistant.

---

## 🗣️ Control por Voz (Assist / Alexa / Google)

Al instalar la integración, se crea automáticamente la entidad:
```text
todo.cesta_casa
```

Puedes interactuar por voz con tus asistentes habituales:
* *"Añade leche y huevos a la lista de la compra"*
* *"¿Qué tengo en la lista de la compra?"*

Los cambios se reflejarán inmediatamente en la aplicación web y viceversa.

---

## 📄 Licencia

Distribuido bajo la licencia **MIT**. Consulta [`LICENSE`](LICENSE) para más detalles.

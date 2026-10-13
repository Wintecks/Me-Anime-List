# Me Anime List

Це веб додаток, який просто розміщується на вашому сервері, у докер контейнері та слугує для відображення списку аніме які ви переглянули. Сам він зберігає ці дані у вашій гугел таблиці, через Apps Script.

#### Встановлення та налаштування
Спочатку необхідно встновити [Git](https://git-scm.com/) та [Docker](https://www.docker.com/), після успішного встановлення та налаштування можна переходити до встановлення самого додатку, для цього потрібно ввести по черзі ці три команди:

```bash
git clone https://github.com/Wintecks/Me-Anime-List.git
```
```bash
cd Me-Anime-List
```
```bash
docker compose up --build -d
```

Після встановлекння і запуску, ви можете перевірити чи запустилися контейнери, ввівши у термінал `docker ps`, воно виведе щось на кшталт:

```bash
CONTAINER ID   IMAGE                      COMMAND                  CREATED              STATUS         PORTS                                                 NAMES
067b5c5bf1c9   me-anime-list-anime-list   "/docker-entrypoint.…"   4 seconds ago        Up 3 seconds   0.0.0.0:8099->80/tcp, :::8099->80/tcp                 anime_list
0b9d0997b446   me-anime-list-backend      "uvicorn main:app --…"   About a minute ago   Up 3 seconds   0.0.0.0:2424->2424/tcp, :::2424->2424/tcp, 8000/tcp   me-anime-list-backend-1
```

Якщо усе запрацювало з першого разу то це успіх!!! <br>
Тепер якщо ви запускали це усебе локально, просто перйдіть за посиланням http://localhost:8099. Якщож ви запустили це у себе, на сервері у докері, то вам необхідно дізнатися ip віртуальної машини чи LXT де встанолений проект, та додати у кінці порт `:8099`, це буде посилання на список. Якщо відкрилася вкладка, яка несхожа на пусту сторінку, це дуже добре далі нам необхідно налаштувати, [Apps Script](https://script.google.com/home), для цього прейдіть у [Google Drive](https://drive.google.com), створіть Google таблицю це те, де буде зберігатися уся інформація про аніме додані у список, дайте їй назву та збережіть, після цього зверху вибіреть перед останій пункти, `Розширення` та пунк у меню `Apps Script`, вас перекине у нове вікно,і де ви вже ситираєте усе що там є і вставляєте наступний код.
```js
// 1. Обробка GET-запиту (завантаження списку аніме)
function doGet(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = sheet.getDataRange().getValues();
  var result = [];

  // Пропускаємо перший рядок (заголовки таблиці)
  for (var i = 1; i < data.length; i++) {
    result.push({
      rowIndex: i + 1,       // Номер рядка в Google Таблиці
      title: data[i][0] || '', // Стовпчик A: Назва
      status: data[i][1] || 'Переглянуто', // Стовпчик B: Статус
      url: data[i][2] || '',    // Стовпчик C: Посилання
      description: data[i][3] || '',   // Стовпчик D: Опис
    });
  }

  return ContentService.createTextOutput(JSON.stringify(result))
    .setMimeType(ContentService.MimeType.JSON);
}

// 2. Обробка POST-запиту (додавання, редагування, видалення)
function doPost(e) {
  var data = {};
  
  try {
    if (e.postData && e.postData.contents) {
      data = JSON.parse(e.postData.contents);
    } else {
      data = e.parameter;
    }
  } catch (err) {
    data = e.parameter;
  }

  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var action = data.action;

  if (action === 'add') {
    sheet.appendRow([data.title, data.status, data.url, data.description]);
  } 
  else if (action === 'edit') {
    var rowIndex = parseInt(data.rowIndex);
    if (rowIndex) {
      sheet.getRange(rowIndex, 1).setValue(data.title);
      sheet.getRange(rowIndex, 2).setValue(data.status);
      sheet.getRange(rowIndex, 3).setValue(data.url);
      sheet.getRange(rowIndex, 4).setValue(data.description);
    }
  } 
  else if (action === 'delete') {
    var rowIndex = parseInt(data.rowIndex);
    if (rowIndex) {
      sheet.deleteRow(rowIndex);
    }
  }

  return ContentService.createTextOutput(JSON.stringify({ status: "success" }))
    .setMimeType(ContentService.MimeType.JSON);
}
```
Після цього справа зверху натискаєте на кнопку `Ввести дію`, і вибираємо `Нове введення в дію`, далі тиснимо `Ввести дію`, копіюємо посилання яке починається на `https://script.google.com`, переходимо у наш додаток, та натискаємо кнопку `Налаштування`, вставляємо наше посилання з [Apps Script](https://script.google.com/home) у відповідне поле та натискаємо зберегти, чикаємо декілька секунд, та пробуємо дадати аніме на сайті, перевіряємо чи воно зявилося у таблиці, якщо воно зяволося, значить усе встановлено та налаштовано вірно. На цьому гайд з встановлення та налаштування закінчився. Приємного користування <3
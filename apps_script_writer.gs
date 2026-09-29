const ETL_SHARED_SECRET =
  PropertiesService
    .getScriptProperties()
    .getProperty('ETL_SHARED_SECRET');

function doPost(e) {

  try {

    const body =
      JSON.parse(
        e.postData.contents
      );

    if (
      !ETL_SHARED_SECRET ||
      body.secret !==
        ETL_SHARED_SECRET
    ) {

      return jsonResponse_({
        ok: false,
        error: 'Unauthorized'
      });

    }

    const expectedSpreadsheetId =
      '1TPsmpYjJbkD-SjynBGKUvbNnnU6fNz2r5CdPmPofm2M';

    if (
      body.spreadsheetId !==
        expectedSpreadsheetId
    ) {

      return jsonResponse_({
        ok: false,
        error: 'Wrong spreadsheet'
      });

    }

    const allowedRanges = new Set([
      'Offense!B4:AC18',
      'Offense!B21:AC37',
      'Offense!B38:AC40',
      'Defense!B4:AC18',
      'Defense!B21:AC37',
      'Defense!B38:AC40'
    ]);

    if (
      !Array.isArray(
        body.data
      ) ||
      body.data.length !== 6
    ) {

      return jsonResponse_({
        ok: false,
        error: 'Invalid payload'
      });

    }

    body.data.forEach(
      item => {

        if (
          !allowedRanges.has(
            item.range
          )
        ) {

          throw new Error(
            'Blocked range: ' +
            item.range
          );

        }

      }
    );

    const ss =
      SpreadsheetApp
        .openById(
          expectedSpreadsheetId
        );

    body.data.forEach(
      item => {

        const parts =
          item.range.split('!');

        const sheet =
          ss.getSheetByName(
            parts[0]
          );

        if (!sheet) {

          throw new Error(
            'Missing sheet: ' +
            parts[0]
          );

        }

        const range =
          sheet.getRange(
            parts[1]
          );

        const values =
          item.values;

        if (
          values.length !==
            range.getNumRows()
        ) {

          throw new Error(
            'Wrong row count for ' +
            item.range
          );

        }

        if (
          values.some(
            row =>
              row.length !==
              range.getNumColumns()
          )
        ) {

          throw new Error(
            'Wrong column count for ' +
            item.range
          );

        }

        range.setValues(
          values
        );

      }
    );

    SpreadsheetApp.flush();

    return jsonResponse_({
      ok: true
    });

  }

  catch (err) {

    return jsonResponse_({
      ok: false,
      error: String(
        err.message ||
        err
      )
    });

  }

}

function jsonResponse_(obj) {

  return ContentService
    .createTextOutput(
      JSON.stringify(obj)
    )
    .setMimeType(
      ContentService.MimeType.JSON
    );

}

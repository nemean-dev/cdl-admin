An admin dashboard for a shopify store.

# Google Sheets
Some parts of the app require data entered into a Google Sheet that is be exposed with the Sheety API. 
Set the following environment variables for connecting Sheety to the app:
- SHEETY_USERNAME
- SHEETY_BEARER

The connected sheety account must expose:
- 'etiquetas' spreadsheet with 'etiquetas' sheet
- 'actualizarCantidades' spreadsheet with 'cantidades' sheet
const { contextBridge } = require('electron');

const apiArg = process.argv.find((arg) => arg.startsWith('--easyget-api-base-url='));
const apiBaseUrl = apiArg
  ? apiArg.slice('--easyget-api-base-url='.length)
  : (process.env.EASYGET_API_BASE_URL || 'http://127.0.0.1:8000/api');

contextBridge.exposeInMainWorld('easygetDesktop', {
  isDesktop: true,
  apiBaseUrl
});

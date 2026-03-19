export {};

declare global {
  interface Window {
    easygetDesktop?: {
      isDesktop: boolean;
      apiBaseUrl: string;
    };
  }
}

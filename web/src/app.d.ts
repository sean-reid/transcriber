declare global {
  namespace App {
    interface Error {
      code?: string;
    }
    interface Locals {}
    interface PageData {}
    interface PageState {}
    interface Platform {
      env?: {
        R2_ACCOUNT_ID?: string;
        R2_ACCESS_KEY_ID?: string;
        R2_SECRET_ACCESS_KEY?: string;
        R2_BUCKET?: string;
        WORKER_URL?: string;
      };
    }
  }
}

export {};

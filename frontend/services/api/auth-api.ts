import apiClient from "./client";

/** Sync a Firebase user record to Supabase users table via backend */
export const authApi = {
  syncUser: async (payload: {
    uid: string;
    email: string;
    display_name: string;
  }): Promise<void> => {
    // Backend upserts into Supabase users table
    await apiClient.post("/auth/sync", payload).catch(() => {
      // Non-fatal — user can still chat even if sync fails
    });
  },
};

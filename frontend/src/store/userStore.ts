import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UserPreferences {
  theme: 'light' | 'dark';
  chatPosition: 'bottom-right' | 'bottom-left';
  primaryColor: string;
  welcomeMessage: string;
}

interface UserState {
  preferences: UserPreferences;
  
  // Actions
  setTheme: (theme: 'light' | 'dark') => void;
  setChatPosition: (position: 'bottom-right' | 'bottom-left') => void;
  setPrimaryColor: (color: string) => void;
  setWelcomeMessage: (message: string) => void;
  resetPreferences: () => void;
}

const defaultPreferences: UserPreferences = {
  theme: 'light',
  chatPosition: 'bottom-right',
  primaryColor: '#3b82f6',
  welcomeMessage: 'Hi! How can I help you find products today?',
};

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      preferences: defaultPreferences,

      setTheme: (theme) => {
        set((state) => ({
          preferences: { ...state.preferences, theme },
        }));
      },

      setChatPosition: (chatPosition) => {
        set((state) => ({
          preferences: { ...state.preferences, chatPosition },
        }));
      },

      setPrimaryColor: (primaryColor) => {
        set((state) => ({
          preferences: { ...state.preferences, primaryColor },
        }));
      },

      setWelcomeMessage: (welcomeMessage) => {
        set((state) => ({
          preferences: { ...state.preferences, welcomeMessage },
        }));
      },

      resetPreferences: () => {
        set({ preferences: defaultPreferences });
      },
    }),
    {
      name: 'easymart-user-storage',
    }
  )
);

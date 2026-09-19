import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0b0d12",
        surface: "#12151c",
        border: "#1f232d",
        accent: "#5b8cff",
      },
    },
  },
  darkMode: "class",
  plugins: [],
};

export default config;

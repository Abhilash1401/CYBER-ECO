import nextConfig from "eslint-config-next/core-web-vitals";

const eslintConfig = [
  ...nextConfig,
  {
    rules: {
      "import/no-anonymous-default-export": "warn",
      "react-hooks/immutability": "off",
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/exhaustive-deps": "warn",
      "@next/next/no-html-link-for-pages": "warn",
    },
  },
];

export default eslintConfig;

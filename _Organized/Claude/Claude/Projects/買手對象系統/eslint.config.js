import eslintConfigNext from 'eslint-config-next';
import tseslint from 'typescript-eslint';

export default [
  ...eslintConfigNext,
  ...tseslint.configs.recommended,
  {
    rules: {
      '@typescript-eslint/no-unused-vars': 'warn',
      '@typescript-eslint/no-explicit-any': 'warn',
      // Allow async fetches in useEffect (common pattern with proper await)
      'react-hooks/set-state-in-effect': 'warn',
      // Allow escaped entities in code comments/SQL blocks
      'react/no-unescaped-entities': 'off',
    },
  },
];

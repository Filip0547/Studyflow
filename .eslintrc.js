module.exports = {
  env: {
    browser: true,
    es2021: true
  },
  extends: [
    'eslint:recommended'
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module'
  },
  rules: {
    'no-undef': 'off' // Disable undefined variable warnings for Jinja2 templates
  },
  overrides: [
    {
      files: ['templates/**/*.html'],
      rules: {
        'no-undef': 'off',
        'no-unused-vars': 'off'
      }
    }
  ]
};
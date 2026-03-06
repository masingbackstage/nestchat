/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{svelte,js,ts}'],
  theme: {
    extend: {
      colors: {
        app: {
          950: '#111318',
          900: '#171b24',
          850: '#1f2430'
        }
      }
    }
  },
  plugins: []
}

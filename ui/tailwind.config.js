export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'Noto Sans Devanagari', 'system-ui', 'sans-serif'],
        serif: ['Noto Serif Devanagari', 'Georgia', 'serif'],
      },
      colors: {
        ink: { DEFAULT: '#14110d', soft: '#4a453c' },
        paper: { DEFAULT: '#faf7f0', card: '#ffffff', edge: '#e6e0d3' },
        seal: { DEFAULT: '#8c2f1f', soft: '#b8543f' },
        mark: '#ffd600',
      },
    },
  },
  plugins: [],
}

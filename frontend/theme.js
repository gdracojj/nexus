try {
  const tema = localStorage.getItem('nexus-tema');
  if (tema === 'dark' || tema === 'light') {
    document.documentElement.dataset.theme = tema;
  }
} catch (_erro) {
  // Armazenamento local pode estar desativado pelo navegador.
}

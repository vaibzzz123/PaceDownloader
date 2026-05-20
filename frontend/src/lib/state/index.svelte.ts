function loadState() {
  if (typeof localStorage === 'undefined') return {};
  try {
    const saved = localStorage.getItem('app-state');
    return saved ? JSON.parse(saved) : {};
  } catch {
    return {};
  }
}

const defaults = {
  darkMode: true,
  spoilerMode: false
};

export const appState = $state({ ...defaults, ...loadState() });

$effect.root(() => {
  $effect(() => {
    // Access each property so Svelte tracks them
    const snapshot = { darkMode: appState.darkMode, spoilerMode: appState.spoilerMode };
    localStorage.setItem('app-state', JSON.stringify(snapshot));
  });
});

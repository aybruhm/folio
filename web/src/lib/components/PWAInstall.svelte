<script lang="ts">
  import { onMount } from 'svelte';
  import { offlineStore } from '$lib/stores/offline';

  interface BeforeInstallPromptEvent extends Event {
    prompt: () => Promise<void>;
    userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
  }

  let deferredPrompt: BeforeInstallPromptEvent | null = null;
  let isIOS = false;
  let isFirefox = false;
  let isMobile = false;
  let showInstallPrompt = false;
  let installError = '';

  onMount(() => {
    // Detect iOS
    isIOS =
      /iPad|iPhone|iPod/.test(navigator.userAgent) &&
      !window.MSStream;

    // Detect Firefox
    isFirefox = /Firefox/.test(navigator.userAgent);

    // Detect mobile
    isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
      navigator.userAgent
    );

    // Listen for beforeinstallprompt event (Chrome, Edge)
    window.addEventListener('beforeinstallprompt', (e: Event) => {
      e.preventDefault();
      deferredPrompt = e as BeforeInstallPromptEvent;
      showInstallPrompt = true;
    });

    // Handle app installed
    window.addEventListener('appinstalled', () => {
      deferredPrompt = null;
      showInstallPrompt = false;
    });
  });

  async function handleInstall() {
    if (!deferredPrompt) {
      installError = 'Install prompt not available';
      return;
    }

    try {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === 'accepted') {
        deferredPrompt = null;
        showInstallPrompt = false;
      }
    } catch (error) {
      installError = 'Installation failed. Please try again.';
      console.error('Installation error:', error);
    }
  }

  function dismissPrompt() {
    showInstallPrompt = false;
  }

  function showIOSInstructions() {
    alert(
      'To install Folio on iOS:\n\n' +
      '1. Open this page in Safari\n' +
      '2. Tap the Share button\n' +
      '3. Scroll down and tap "Add to Home Screen"\n' +
      '4. Tap "Add" in the top right'
    );
  }

  function showFirefoxInstructions() {
    alert(
      'To install Folio on Firefox:\n\n' +
      '1. Look for the installation icon in the address bar (looks like a house with an arrow)\n' +
      '2. Or tap the menu (⋮) → "Install App"\n' +
      '3. Confirm the installation\n' +
      '4. App appears on your home screen or app drawer'
    );
  }

</script>

<div class="pwa-install-container">
  {#if showInstallPrompt && deferredPrompt}
    <div class="install-banner">
      <div class="install-content">
        <div class="install-icon">
          <img src="/icon-192.png" alt="Folio" width="48" height="48" />
        </div>
        <div class="install-text">
          <h3>Install Folio</h3>
          <p>Get Folio on your device for quick access and offline support</p>
        </div>
        <div class="install-actions">
          <button class="btn-install" on:click={handleInstall}>Install</button>
          <button class="btn-dismiss" on:click={dismissPrompt}>Dismiss</button>
        </div>
      </div>
      {#if installError}
        <div class="install-error">{installError}</div>
      {/if}
    </div>
  {/if}

  {#if isIOS && isMobile && !$offlineStore.isOnline}
    <div class="offline-badge">
      <span>You're offline</span>
    </div>
  {/if}

  {#if isMobile && isIOS}
    <div class="ios-install-hint">
      <button class="btn-link" on:click={showIOSInstructions}>
        📱 Add to Home Screen
      </button>
    </div>
  {/if}

  {#if isFirefox}

  {/if}
</div>

<style>
  .pwa-install-container {
    position: relative;
  }

  .install-banner {
    background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%);
    color: white;
    padding: 16px;
    border-radius: 8px;
    margin-bottom: 16px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .install-content {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .install-icon {
    flex-shrink: 0;
  }

  .install-icon img {
    border-radius: 8px;
  }

  .install-text {
    flex: 1;
  }

  .install-text h3 {
    margin: 0 0 4px 0;
    font-size: 16px;
    font-weight: 600;
  }

  .install-text p {
    margin: 0;
    font-size: 14px;
    opacity: 0.9;
  }

  .install-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }

  .btn-install,
  .btn-dismiss {
    padding: 8px 16px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .btn-install {
    background: white;
    color: #1e40af;
  }

  .btn-install:hover {
    transform: scale(1.05);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  }

  .btn-dismiss {
    background: rgba(255, 255, 255, 0.2);
    color: white;
  }

  .btn-dismiss:hover {
    background: rgba(255, 255, 255, 0.3);
  }

  .install-error {
    margin-top: 8px;
    padding: 8px;
    background: rgba(239, 68, 68, 0.2);
    border-radius: 4px;
    font-size: 13px;
  }

  .offline-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    background: #f97316;
    color: white;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
  }

  .badge-icon {
    font-size: 14px;
  }

  .ios-install-hint {
    margin-top: 8px;
  }

  .firefox-install-hint {
    margin-top: 8px;
  }

  .btn-link {
    background: none;
    border: none;
    color: #3b82f6;
    cursor: pointer;
    font-size: 13px;
    padding: 0;
    text-decoration: underline;
  }

  .btn-link:hover {
    color: #1e40af;
  }

  @media (max-width: 640px) {
    .install-content {
      flex-direction: column;
      gap: 12px;
    }

    .install-actions {
      width: 100%;
    }

    .btn-install,
    .btn-dismiss {
      flex: 1;
    }
  }
</style>

/**
 * web/settings_frame.js – Cadre de configuration auto-ajouté à la page Settings.
 * Version: 0.2.0
 *
 * Le Bridge monte ce composant dans la zone Settings via register_ui_contribution.
 * Conforme aux spécifications §9 et §10.4 de plugins_architecture.md.
 */

export function mountSettings(container, bridge) {
  const t = bridge.i18n.t;
  const pluginVersion = bridge.plugins.getVersion('example_plugin') || '0.2.0';

  container.innerHTML = `
    <fieldset class="plugin-settings-frame example-settings">
      <legend>${t('example_settings_title')}</legend>
      
      <!-- En-tête avec version et mise à jour -->
      <div class="setting-header">
        <span class="plugin-version">${t('example_settings_version')}: <strong>${pluginVersion}</strong></span>
        <div class="update-actions">
          <button id="example-check-update" class="btn btn-secondary btn-sm">
            ${t('example_settings_check_update')}
          </button>
          <button id="example-update-plugin" class="btn btn-secondary btn-sm" disabled>
            ${t('example_settings_update_plugin')}
          </button>
          <span id="example-update-feedback"></span>
        </div>
      </div>

      <!-- Options de configuration -->
      <div class="setting-row">
        <label>
          <input type="checkbox" id="example-verbose" />
          ${t('example_settings_option1_label')}
        </label>
        <small>${t('example_settings_option1_help')}</small>
      </div>

      <!-- Mode debug (§10.4) -->
      <div class="setting-row">
        <label>
          <input type="checkbox" id="example-debug-mode" />
          ${t('example_settings_debug_mode_label')}
        </label>
        <small>${t('example_settings_debug_mode_help')}</small>
      </div>

      <!-- Notifications (§10.4) -->
      <div class="setting-row">
        <label>
          <input type="checkbox" id="example-notifications" checked />
          ${t('example_settings_notifications_label')}
        </label>
        <small>${t('example_settings_notifications_help')}</small>
      </div>

      <!-- Actions -->
      <div class="setting-actions">
        <button id="example-settings-save" class="btn btn-primary">
          ${t('example_settings_save')}
        </button>
        <button id="example-view-changelog" class="btn btn-secondary">
          ${t('example_settings_view_changelog')}
        </button>
        <button id="example-reset-settings" class="btn btn-warning">
          ${t('example_settings_reset')}
        </button>
        <span id="example-settings-feedback"></span>
      </div>
    </fieldset>
  `;

  // === Éléments du DOM ===
  const verboseCheckbox = container.querySelector('#example-verbose');
  const debugModeCheckbox = container.querySelector('#example-debug-mode');
  const notificationsCheckbox = container.querySelector('#example-notifications');
  const saveBtn = container.querySelector('#example-settings-save');
  const feedback = container.querySelector('#example-settings-feedback');
  const checkUpdateBtn = container.querySelector('#example-check-update');
  const updatePluginBtn = container.querySelector('#example-update-plugin');
  const updateFeedback = container.querySelector('#example-update-feedback');
  const viewChangelogBtn = container.querySelector('#example-view-changelog');
  const resetSettingsBtn = container.querySelector('#example-reset-settings');

  let latestVersion = null;

  // === Charger les valeurs actuelles ===
  bridge.config.get('example_plugin').then(cfg => {
    verboseCheckbox.checked = cfg?.verbose ?? false;
    debugModeCheckbox.checked = cfg?.debug_mode ?? false;
    notificationsCheckbox.checked = cfg?.notifications ?? true;
  });

  // === Sauvegarde ===
  saveBtn.addEventListener('click', async () => {
    try {
      await bridge.config.set('example_plugin', {
        verbose: verboseCheckbox.checked,
        debug_mode: debugModeCheckbox.checked,
        notifications: notificationsCheckbox.checked
      });
      feedback.textContent = t('example_settings_saved');
      feedback.className = 'feedback-success';
      
      // Notification si activée
      if (notificationsCheckbox.checked) {
        bridge.notify.success(t('example_settings_saved'));
      }
    } catch (err) {
      feedback.textContent = t('example_settings_error');
      feedback.className = 'feedback-error';
    }
  });

  // === Check for update ===
  checkUpdateBtn.addEventListener('click', async () => {
    updateFeedback.textContent = '';
    try {
      const info = await bridge.plugins.checkUpdate('example_plugin');
      if (info.updateAvailable) {
        latestVersion = info.latestVersion;
        updateFeedback.textContent = t('example_settings_update_available').replace('{version}', latestVersion);
        updateFeedback.className = 'feedback-warning';
        updatePluginBtn.disabled = false;
      } else {
        updateFeedback.textContent = t('example_settings_up_to_date');
        updateFeedback.className = 'feedback-success';
        updatePluginBtn.disabled = true;
      }
    } catch (err) {
      updateFeedback.textContent = t('example_settings_update_error');
      updateFeedback.className = 'feedback-error';
    }
  });

  // === Update plugin ===
  updatePluginBtn.addEventListener('click', async () => {
    if (!latestVersion) return;
    updateFeedback.textContent = t('example_settings_updating');
    updateFeedback.className = '';
    try {
      await bridge.plugins.update('example_plugin', latestVersion);
      updateFeedback.textContent = t('example_settings_update_success');
      updateFeedback.className = 'feedback-success';
      updatePluginBtn.disabled = true;
    } catch (err) {
      updateFeedback.textContent = t('example_settings_update_error');
      updateFeedback.className = 'feedback-error';
    }
  });

  // === View changelog (§10.4) ===
  viewChangelogBtn.addEventListener('click', async () => {
    try {
      const changelog = await bridge.api.get('/example/changelog');
      bridge.modal.show({
        title: t('example_changelog_title'),
        content: changelog.content,
        format: 'markdown'
      });
    } catch (err) {
      bridge.notify.error(t('example_changelog_error'));
    }
  });

  // === Reset settings (§8 remote reset support) ===
  resetSettingsBtn.addEventListener('click', async () => {
    if (!confirm(t('example_settings_reset_confirm'))) return;
    try {
      await bridge.api.post('/example/reset-settings');
      // Recharger les valeurs
      const cfg = await bridge.config.get('example_plugin');
      verboseCheckbox.checked = cfg?.verbose ?? false;
      debugModeCheckbox.checked = cfg?.debug_mode ?? false;
      notificationsCheckbox.checked = cfg?.notifications ?? true;
      feedback.textContent = t('example_settings_reset_success');
      feedback.className = 'feedback-success';
    } catch (err) {
      feedback.textContent = t('example_settings_error');
      feedback.className = 'feedback-error';
    }
  });
}

export function unmountSettings(container) {
  container.innerHTML = '';
}

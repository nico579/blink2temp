package com.nico.blink2temp

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.core.content.FileProvider
import androidx.lifecycle.ViewModelProvider
import com.nico.blink2temp.ui.BlinkScreen
import com.nico.blink2temp.update.UpdatePhase
import com.nico.blink2temp.update.UpdateViewModel

class MainActivity : ComponentActivity() {
    private val model: AppViewModel by viewModels {
        ViewModelProvider.AndroidViewModelFactory(application)
    }
    private val updates: UpdateViewModel by viewModels {
        ViewModelProvider.AndroidViewModelFactory(application)
    }

    private val installPermission = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult(),
    ) {
        if (packageManager.canRequestPackageInstalls()) {
            updates.requestInstall()
        } else {
            updates.fail("L'autorisation d'installer la mise à jour n'a pas été accordée.")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val state by model.state.collectAsState()
            val updateState by updates.state.collectAsState()

            LaunchedEffect(updateState.installRequested) {
                if (updateState.installRequested) {
                    if (!packageManager.canRequestPackageInstalls()) {
                        updates.permissionRequired()
                    } else {
                        updates.consumeInstallRequest()
                        try {
                            val file = updateState.downloaded?.file ?: return@LaunchedEffect
                            val uri = FileProvider.getUriForFile(
                                this@MainActivity,
                                "$packageName.updates",
                                file,
                            )
                            startActivity(
                                Intent(Intent.ACTION_VIEW)
                                    .setDataAndType(uri, "application/vnd.android.package-archive")
                                    .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION),
                            )
                        } catch (_: Exception) {
                            updates.fail("Impossible d'ouvrir l'installateur Android.")
                        }
                    }
                }
            }

            BlinkScreen(
                state = state,
                onConnect = model::connect,
                onTwoFactor = model::submitTwoFactor,
                onCancelTwoFactor = model::cancelTwoFactor,
                onRefresh = model::relever,
                onToggleCamera = model::toggleCamera,
                onSelectAll = model::selectAll,
                onSelectNone = model::selectNone,
                onWindowChange = model::changeWindow,
                onLogout = model::logout,
                onClearHistory = model::clearHistory,
                onDismissMessage = model::dismissMessage,
                updateState = updateState,
                onUpdates = updates::open,
                onUpdateClose = updates::dismiss,
                onUpdateCheck = updates::check,
                onUpdateAction = {
                    if (updateState.phase == UpdatePhase.PERMISSION) {
                        try {
                            installPermission.launch(
                                Intent(
                                    Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                                    Uri.parse("package:$packageName"),
                                ),
                            )
                        } catch (_: Exception) {
                            updates.fail("Impossible d'ouvrir les réglages d'installation Android.")
                        }
                    } else {
                        updates.primaryAction()
                    }
                },
            )
        }
    }
}

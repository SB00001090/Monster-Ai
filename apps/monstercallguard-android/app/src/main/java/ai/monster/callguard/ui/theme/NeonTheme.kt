package ai.monster.callguard.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val NeonCyan = Color(0xFF00F5FF)
val NeonMagenta = Color(0xFFFF00FF)
val NeonGreen = Color(0xFF39FF14)
val DarkBg = Color(0xFF0A0E17)
val DarkSurface = Color(0xFF12182A)

private val scheme = darkColorScheme(
    primary = NeonCyan,
    secondary = NeonMagenta,
    tertiary = NeonGreen,
    background = DarkBg,
    surface = DarkSurface,
    onBackground = Color(0xFFE8F4FF),
    onSurface = Color(0xFFE8F4FF),
)

@Composable
fun MonsterCallGuardTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = scheme, content = content)
}
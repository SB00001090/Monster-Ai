package ai.monster.callguard.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "location_records")
data class LocationRecord(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val latitude: Double,
    val longitude: Double,
    val accuracyM: Float,
    val source: String,
    val simPresent: Boolean,
    val timestampMs: Long,
    val synced: Boolean = false,
)
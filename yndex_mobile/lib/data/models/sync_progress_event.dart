class SyncProgressEvent {
  final String type; // 'progress', 'complete', 'error'
  final String stage;
  final int percent;
  final int current;
  final int total;
  final String message;
  final int? tracksSynced;
  final bool isComplete;
  final bool isError;

  SyncProgressEvent({
    required this.type,
    required this.stage,
    required this.percent,
    required this.current,
    required this.total,
    required this.message,
    this.tracksSynced,
    this.isComplete = false,
    this.isError = false,
  });

  factory SyncProgressEvent.fromJson(Map<String, dynamic> json) {
    final type = json['type'] as String? ?? 'progress';
    final stage = json['stage'] as String? ?? '';
    final percent = (json['percent'] as num?)?.toInt() ?? 0;
    final current = (json['current'] as num?)?.toInt() ?? 0;
    final total = (json['total'] as num?)?.toInt() ?? 0;
    final message = json['message'] as String? ?? '';
    final tracksSynced = (json['tracks_synced'] as num?)?.toInt();

    return SyncProgressEvent(
      type: type,
      stage: stage,
      percent: percent,
      current: current,
      total: total,
      message: message,
      tracksSynced: tracksSynced,
      isComplete: type == 'complete',
      isError: type == 'error',
    );
  }

  factory SyncProgressEvent.error(String errorMessage) {
    return SyncProgressEvent(
      type: 'error',
      stage: 'error',
      percent: 0,
      current: 0,
      total: 0,
      message: errorMessage,
      isError: true,
    );
  }
}

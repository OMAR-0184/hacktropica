/// Bottom sheet to start a new learning session.
library;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../services/api_client.dart';
import '../../viewmodels/session_viewmodel.dart';

class NewSessionSheet extends ConsumerStatefulWidget {
  const NewSessionSheet({super.key});

  @override
  ConsumerState<NewSessionSheet> createState() => _NewSessionSheetState();
}

class _NewSessionSheetState extends ConsumerState<NewSessionSheet> {
  final _topicCtrl = TextEditingController();
  String _courseMode = 'detailed';
  String _traversalMode = 'dfs';
  bool _loading = false;
  String? _error;
  List<String>? _suggestions;

  Future<void> _start() async {
    final topic = _topicCtrl.text.trim();
    if (topic.isEmpty) {
      setState(() => _error = 'Topic cannot be empty.');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
      _suggestions = null;
    });

    try {
      final sessionId =
          await ref.read(sessionListProvider.notifier).startSession(
                topic: topic,
                courseMode: _courseMode,
                traversalMode: _traversalMode,
              );
      if (mounted) {
        Navigator.pop(context);
        context.go('/learn/$sessionId');
      }
    } on DioException catch (e) {
      final data = e.response?.data;
      // Parse 422 suggestions
      if (e.response?.statusCode == 422 && data is Map<String, dynamic>) {
        final detail = data['detail'];
        if (detail is Map<String, dynamic>) {
          _error = detail['message'] as String?;
          final sug = detail['suggestions'];
          if (sug is List) {
            _suggestions = sug.map((e) => e.toString()).toList();
          }
        } else {
          _error = parseApiError(data);
        }
      } else {
        _error = parseApiError(data);
      }
      setState(() {});
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _topicCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding:
          EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Container(
        padding: const EdgeInsets.fromLTRB(24, 12, 24, 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Drag handle
            Center(
              child: Container(
                width: 40,
                height: 4,
                margin: const EdgeInsets.only(bottom: 20),
                decoration: BoxDecoration(
                  color: AppColors.border,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),

            const Text(
              'Start a new session',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 20),

            // Topic
            TextField(
              controller: _topicCtrl,
              decoration: const InputDecoration(
                labelText: 'TOPIC',
                hintText: 'e.g. Data Structures & Algorithms',
                prefixIcon: Icon(Icons.topic_outlined, size: 18),
              ),
              enabled: !_loading,
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => _start(),
            ),
            const SizedBox(height: 16),

            // Course mode
            const Text('Course Mode',
                style: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 12,
                    fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'detailed', label: Text('Detailed')),
                ButtonSegment(value: 'micro', label: Text('Micro')),
              ],
              selected: {_courseMode},
              onSelectionChanged: (s) =>
                  setState(() => _courseMode = s.first),
              style: SegmentedButton.styleFrom(
                backgroundColor: AppColors.surface2,
                selectedBackgroundColor: AppColors.primary500.withAlpha(30),
                selectedForegroundColor: AppColors.primary400,
                foregroundColor: AppColors.textMuted,
              ),
            ),
            const SizedBox(height: 16),

            // Traversal mode
            const Text('Traversal Mode',
                style: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 12,
                    fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(
                    value: 'dfs',
                    label: Text('DFS (Deep)'),
                    icon: Icon(Icons.arrow_downward, size: 14)),
                ButtonSegment(
                    value: 'bfs',
                    label: Text('BFS (Wide)'),
                    icon: Icon(Icons.swap_horiz, size: 14)),
              ],
              selected: {_traversalMode},
              onSelectionChanged: (s) =>
                  setState(() => _traversalMode = s.first),
              style: SegmentedButton.styleFrom(
                backgroundColor: AppColors.surface2,
                selectedBackgroundColor: AppColors.primary500.withAlpha(30),
                selectedForegroundColor: AppColors.primary400,
                foregroundColor: AppColors.textMuted,
              ),
            ),
            const SizedBox(height: 20),

            // Error + suggestions
            if (_error != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.error.withAlpha(15),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppColors.error.withAlpha(40)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(_error!,
                        style: const TextStyle(
                            color: AppColors.error, fontSize: 13)),
                    if (_suggestions != null && _suggestions!.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      const Text('Try:',
                          style: TextStyle(
                              color: AppColors.textMuted, fontSize: 11)),
                      const SizedBox(height: 4),
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: _suggestions!
                            .map((s) => ActionChip(
                                  label: Text(s,
                                      style: const TextStyle(fontSize: 12)),
                                  onPressed: () {
                                    _topicCtrl.text = s;
                                    setState(() {
                                      _error = null;
                                      _suggestions = null;
                                    });
                                  },
                                ))
                            .toList(),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Start button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _loading ? null : _start,
                child: _loading
                    ? const SizedBox(
                        height: 18,
                        width: 18,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white),
                      )
                    : const Text('Start Learning'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

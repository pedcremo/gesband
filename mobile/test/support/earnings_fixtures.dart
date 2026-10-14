// Respuestas sintéticas de las actividades remuneradas y de
// `GET /api/v1/members/me/earnings`.
//
// Contrastadas el 14/10/2026 con el servidor: `earningsServerJson` es una
// respuesta real de las pruebas del backend (la forma coincide con el
// contrato; `paid_at` llega con microsegundos). Las demás reproducen el
// contrato con datos sintéticos. Si cambia la forma, se cambia aquí, en el
// servidor y en contracts/openapi.yaml a la vez.

/// Campos de una actividad remunerada dentro de `ActivitySerializer`.
const paidActivityFields = <String, dynamic>{
  'is_paid': true,
  'fee_amount': '25.00',
};

/// Campos de una actividad no remunerada.
const unpaidActivityFields = <String, dynamic>{
  'is_paid': false,
  'fee_amount': null,
};

/// Ejemplo del contrato: una actividad adeudada.
Map<String, dynamic> earningsContractJson() => {
      'currency': 'EUR',
      'owed_total': '50.00',
      'paid_total': '25.00',
      'items': [
        {
          'invitation': '8d2f0000-0000-4000-8000-000000000001',
          'activity': {
            'id': '5a1e0000-0000-4000-8000-000000000001',
            'title': 'Concierto de Santa Cecilia',
            'starts_at': '2026-11-22T17:00:00Z',
          },
          'amount': '25.00',
          'status': 'owed',
          'paid_at': null,
        },
      ],
    };

/// Mismo contrato con una adeudada y una pagada, coherente con los totales.
Map<String, dynamic> earningsWithPaidJson() => {
      'currency': 'EUR',
      'owed_total': '50.00',
      'paid_total': '25.00',
      'items': [
        {
          'invitation': '8d2f0000-0000-4000-8000-000000000001',
          'activity': {
            'id': '5a1e0000-0000-4000-8000-000000000001',
            'title': 'Concierto de Santa Cecilia',
            'starts_at': '2026-11-22T17:00:00Z',
          },
          'amount': '25.00',
          'status': 'owed',
          'paid_at': null,
        },
        {
          'invitation': '8d2f0000-0000-4000-8000-000000000002',
          'activity': {
            'id': '5a1e0000-0000-4000-8000-000000000002',
            'title': 'Procesión de San Agustín',
            'starts_at': '2026-08-28T19:00:00Z',
          },
          'amount': '25.00',
          'status': 'owed',
          'paid_at': null,
        },
        {
          'invitation': '8d2f0000-0000-4000-8000-000000000003',
          'activity': {
            'id': '5a1e0000-0000-4000-8000-000000000003',
            'title': 'Fiestas de Moros y Cristianos',
            'starts_at': '2026-02-01T10:00:00Z',
          },
          'amount': '25.00',
          'status': 'paid',
          'paid_at': '2026-03-05T10:30:00Z',
        },
      ],
    };

/// Sin actividades remuneradas con asistencia registrada.
Map<String, dynamic> emptyEarningsJson() => {
      'currency': 'EUR',
      'owed_total': '0.00',
      'paid_total': '0.00',
      'items': <Map<String, dynamic>>[],
    };

/// Respuesta real de `GET /api/v1/members/me/earnings/` (pruebas del backend,
/// 14/10/2026): una adeudada y una pagada.
Map<String, dynamic> earningsServerJson() => {
      'currency': 'EUR',
      'owed_total': '30.00',
      'paid_total': '25.00',
      'items': [
        {
          'invitation': '164a3442-9ddd-4468-a4aa-f093890df6b9',
          'activity': {
            'id': '960101c2-a16d-4460-9152-cf544ddd8ccf',
            'title': 'Concierto de Santa Cecilia',
            'starts_at': '2026-11-22T17:00:00Z',
          },
          'amount': '30.00',
          'status': 'owed',
          'paid_at': null,
        },
        {
          'invitation': '49508948-8fea-48c6-933c-0c2ef5fad322',
          'activity': {
            'id': '7d67b110-c258-487e-be43-439e92ed1ef3',
            'title': 'Concierto de primavera',
            'starts_at': '2026-10-17T17:00:00Z',
          },
          'amount': '25.00',
          'status': 'paid',
          'paid_at': '2026-10-14T20:19:46.483508Z',
        },
      ],
    };

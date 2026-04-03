import xmlrpc.client
from django.conf import settings


def _client():
    return xmlrpc.client.ServerProxy(settings.GNURADIO_URL, allow_none=True)


def set_pathloss(ue_id: int, value: float) -> dict:
    try:
        c = _client()
        method = getattr(c, f'set_ue{ue_id}_path_loss_db')
        method(float(value))
        return {'ok': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def set_noise(noise_type: str, level: float) -> dict:
    """
    noise_type: none | awgn | fading | shadow | doppler | interf
    level: dB value
    """
    try:
        c = _client()
        # Map noise type to GNU Radio method — adjust to your flowgraph
        method_map = {
            'awgn':    'set_noise_level',
            'fading':  'set_fading_level',
            'shadow':  'set_shadowing_level',
            'doppler': 'set_doppler_level',
            'interf':  'set_interference_level',
        }
        if noise_type in method_map:
            getattr(c, method_map[noise_type])(float(level))
        return {'ok': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

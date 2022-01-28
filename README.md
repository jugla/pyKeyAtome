# KeyAtome PyPi
![GitHub release](https://img.shields.io/github/release/jugla/pyKeyAtome)

Get your energy consumption data from Atome, a Linky-compatible device made by Total/Direct-Energie.
A account can have several linky. With this library, you can adress them one by one

### Installing
```
pip install pykeyatome
```

## Use
The `__main__.py` is provided to show an example of use.

4 types of function provided by client.py in `AtomeClient` class:
- login : to be logged to the server
- get_user_reference : to know which linky you have adressed 
- get_live : to retrieve live statistics (instant power)
- get_consumption(period) : to retrieve the consumption since a period (day/week/month/year)

## Acknowledgments
* Thanks to k20human for the original inspiration with https://github.com/k20human/domoticz-atome
* Thanks to reverse engineering of Atome IOS APP performed by BaQs.
* This project is a fork of https://github.com/BaQs/pyAtome (seems to be unmaintained)

### Breaking change
**V1.2.0** Since this version PyAtomeError exception is no more used. Instead login return *False* if error , and live/consumption return *None*

**V1.3.0** Login return *None* if error

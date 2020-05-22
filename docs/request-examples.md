Curl for development
====================

During development it can be useful to have the WiFi setup process listening for requests on your main network rather than starting its own access point.

In this state you can use `curl` to experiment with the basic REST interface of the setup process.

Example requests
----------------

Set the address to use for all requests:

    $ ADDR=192.168.0.178

Request the root document:

    $ curl -v $ADDR

Or:

    $ curl -v $ADDR/index.html

Deliberately generate a 404 (Not Found):

    $ curl -v $ADDR/unknown

Set things up to make including the JSON accept header easier and make the same request with this header:

    $ JSON='Accept: application/json'
    $ curl -v -H "$JSON" $ADDR/unknown

The response body now comes back as JSON rather than HTML.

Some requests only return JSON:

    $ curl -v $ADDR/api/access-points

There's a slight pause for this request as it goes off and scans for access points.

If you've got `jq` installed try it again like so:

    $ curl -s -v $ADDR/api/access-points | jq .

Try the authentication endpoint:

    $ curl -v -H "$JSON" --data 'ssid=alpha&password=beta' $ADDR/api/access-point

Get it to fail by not providing an SSID:

    $ curl -v -H "$JSON" --data 'password=beta' $ADDR/api/access-point

Oddy `-v` doesn't show the data sent with `--data`, if you want to see what exactly is sent you need to use `--trace-ascii`:

    $ curl --trace-ascii - -H "$JSON" --data 'ssid=alpha&password=beta' $ADDR/api/access-point

The output isn't very readable - but everything is there.
